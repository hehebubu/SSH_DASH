import flet as ft
import json
import os
import subprocess
import paramiko
from typing import Dict, List
from datetime import datetime

class SSHConnector:
    def __init__(self, page: ft.Page):
        self.page = page
        self.config = self.load_config()
        self.setup_page()
        self.setup_icons()  # Set up icons
        self.create_ui()

    def load_config(self) -> Dict:
        try:
            with open('servers.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.show_error("servers.json file not found.")
            return {"credentials": {"default_username": "", "default_password": ""}, "servers": []}


    def setup_icons(self):
        """Method to set up icons for deprecated warning fix"""
        self.person_icon = ft.Icons.PERSON
        self.lock_icon = ft.Icons.LOCK

    def create_ui(self):
        # Left panel (server list)
        left_panel = self.create_left_panel()


        # Top button panel added
        top_panel = ft.Row(
            controls=[
                ft.ElevatedButton(
                    "Check All GPU Status",
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE,
                    on_click=self.handle_check_all_gpu_status,
                ),
                ft.ElevatedButton(
                    "Linux Manual",
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.GREEN,
                    on_click=self.handle_open_manual,
                ),
                ft.ElevatedButton(
                    "Long-term Application",
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.ORANGE,
                    on_click=self.handle_open_longterm,
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
            spacing=10,  # Spacing between buttons
        )

        # Right panel (GPU status)
        self.gpu_status_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("GPU Status", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("Select a server to check GPU status.",
                        size=14, color=ft.Colors.GREY_600),
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            padding=20,
            width=600,
            expand=True,
        )

        # Overall layout
        main_layout = ft.Column(
            controls=[
                top_panel,
                ft.Row(
                    controls=[
                        left_panel,
                        ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                        self.gpu_status_container
                    ],
                    expand=True,
                )
            ],
            expand=True,
        )

        self.page.add(main_layout)
        self.page.update()


    def handle_check_all_gpu_status(self, e):
        """GPU Status Check Button Handler - Redirect to website"""
        import webbrowser
        webbrowser.open('http://10.201.135.113:8890')

    def handle_open_manual(self, e):
        """Linux Manual Button Handler"""
        import webbrowser
        webbrowser.open('https://dashlab-manual.netlify.app')

    def handle_open_longterm(self, e):
        """Long-term Application Excel Link Button Handler"""
        import webbrowser
        webbrowser.open('https://o365skku.sharepoint.com/:x:/s/DASHLab/ES3hyEE2yDxIu4Ch3uvCuM8BcfJu9or5Qokdp5jU4FFHBA?e=CenLjo')

    def setup_page(self):
        self.page.title = "SSH Server Connector"
        self.page.window.width = 1400
        self.page.window.height = 1000
        self.page.padding = 20
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(color_scheme_seed="blue")


    async def check_all_gpu_status(self):
        try:
            total_servers = len(self.config["servers"])
            current_server = 0

            # UI to display progress
            progress_bar = ft.ProgressBar(width=400, value=0)
            progress_text = ft.Text("Preparing to connect to servers...", size=14, color=ft.colors.GREY_600)
            server_status_text = ft.Text("", size=14, color=ft.colors.GREY_600)

            loading_content = ft.Column(
                controls=[
                    ft.Text("Loading All GPU Status...", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(height=20),
                    progress_bar,
                    ft.Container(height=10),
                    progress_text,
                    server_status_text,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            self.gpu_status_container.content = loading_content
            self.page.update()

            # List to store status information of all servers
            all_status = []

            # Check status for each server
            for server in self.config["servers"]:
                current_server += 1
                progress = current_server / total_servers

                # Update progress
                progress_bar.value = progress
                progress_text.value = f"Progress: {current_server}/{total_servers} ({int(progress * 100)}%)"
                server_status_text.value = f"Current Server: {server['name']} ({server['ip']})"
                self.page.update()

                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                    username = self.username_field.value or self.config["credentials"]["default_username"]
                    password = self.password_field.value or self.config["credentials"]["default_password"]

                    server_status_text.value = f"Connecting to '{server['name']}'..."
                    self.page.update()

                    try:
                        ssh_key_path = os.path.expanduser('~/.ssh/id_rsa')
                        ssh.connect(server["ip"], username=username, key_filename=ssh_key_path)
                    except Exception:
                        ssh.connect(server["ip"], username=username, password=password)

                    server_status_text.value = f"Collecting GPU information from '{server['name']}'..."
                    self.page.update()

                    stdin, stdout, stderr = ssh.exec_command('nvidia-smi')
                    output = stdout.read().decode()

                    all_status.append({
                        "server_name": server["name"],
                        "status": self.format_gpu_info(output, ssh) # Pass ssh client for process info
                    })

                    ssh.close()

                except Exception as e:
                    all_status.append({
                        "server_name": server["name"],
                        "status": f"Connection Failed: {str(e)}"
                    })

            # Display progress completion
            progress_text.value = "All server information collected!"
            server_status_text.value = "Generating results..."
            self.page.update()

            # Combine all status information into a single string
            combined_status = "\n\n".join([
                f"=== {status['server_name']} ===\n{status['status']}"
                for status in all_status
            ])

            # Final UI update
            status_content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Overall GPU Status", size=20, weight=ft.FontWeight.BOLD),
                            ft.Container(width=20),
                            ft.Text(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                size=14, color=ft.colors.GREY_600),
                        ],
                    ),
                    ft.Divider(height=1, color=ft.colors.GREY_300),
                    ft.Container(
                        content=ft.Text(combined_status,
                                    size=14,
                                    font_family="Consolas",
                                    selectable=True),
                        bgcolor=ft.colors.GREY_50,
                        padding=10,
                        border_radius=5,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            )

            self.gpu_status_container.content = status_content
            self.page.update()

        except Exception as e:
            self.show_error(f"Failed to check GPU status: {str(e)}")



    def create_left_panel(self):
        # Credentials Section
        self.username_field = ft.TextField(
            label="Username",
            prefix_icon=ft.Icons.PERSON,
            border_radius=10,
            value=self.config["credentials"]["default_username"],
            width=250,
        )
        self.password_field = ft.TextField(
            label="Password",
            prefix_icon=ft.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            border_radius=10,
            value=self.config["credentials"]["default_password"],
            width=250,
        )


        credentials_column = ft.Column(
            controls=[
                ft.Text("SSH Server Connector", size=24, weight=ft.FontWeight.BOLD),
                self.username_field,
                self.password_field,
            ],
            spacing=20,
        )

        # Server List
        server_list = ft.Column(
            controls=[self.create_server_card(server) for server in self.config["servers"]],
            scroll=ft.ScrollMode.AUTO,
            spacing=10,
        )

        return ft.Container(
            content=ft.Column(
                controls=[
                    credentials_column,
                    ft.Divider(height=1, color=ft.colors.GREY_300),
                    ft.Text("Server List", size=16, weight=ft.FontWeight.BOLD),
                    server_list,
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=20,
            ),
            width=400,
            padding=20,
        )

    def create_server_card(self, server: Dict) -> ft.Card:
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(server["name"], size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(f"IP: {server['ip']}", size=14, color=ft.Colors.GREY_700),
                        ft.Text(f"GPU: {server['gpu_count']}x {server['gpu_spec']}",
                               size=14, color=ft.Colors.GREY_700),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton(
                                    "Connect",
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.BLUE,
                                    on_click=lambda e, s=server: self.connect_to_server(s),
                                ),
                                ft.ElevatedButton(
                                    "GPU Status",
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.GREEN,
                                    on_click=lambda e, s=server: self.update_gpu_status(s),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                ),
                padding=20,
            ),
        )


    def format_user_info(self, output: str) -> str:
        """Formats user information"""
        if not output.strip():
            return "No users currently logged in."

        lines = output.strip().split('\n')

        # Table settings
        table_width = 75
        user_width = 15
        tty_width = 10
        from_width = 20
        login_width = 15
        what_width = table_width - user_width - tty_width - from_width - login_width - 9  # Separator margins

        # Table creation
        border = "+" + "-" * table_width + "+"
        header = f"| {'User':^{user_width}} | {'TTY':^{tty_width}} | {'From':^{from_width}} | {'Login Time':^{login_width}} | {'What':^{what_width}} |"

        formatted_output = [
            border,
            header,
            border
        ]

        # Add user information
        for line in lines:
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 5:
                user = parts[0][:user_width]
                tty = parts[1][:tty_width]
                from_loc = parts[2][:from_width]
                login_time = ' '.join(parts[3:5])[:login_width]
                what = ' '.join(parts[5:])[:what_width] if len(parts) > 5 else ''

                formatted_line = f"| {user:<{user_width}} | {tty:<{tty_width}} | {from_loc:<{from_width}} | {login_time:<{login_width}} | {what:<{what_width}} |"
                formatted_output.append(formatted_line)

        formatted_output.append(border)
        return '\n'.join(formatted_output)


    def format_gpu_info(self, output: str, ssh_client: paramiko.SSHClient) -> str:
        """Parses nvidia-smi output and formats it neatly"""
        try:
            lines = output.split('\n')
            gpus = []
            in_process_section = False

            # Parse basic GPU information
            for i, line in enumerate(lines):
                if '|   ' in line and 'NVIDIA' in line:
                    try:
                        parts = [p.strip() for p in line.split('|')]
                        gpu_info = parts[1].strip().split()
                        gpu_id = gpu_info[0]

                        # Performance information from the next line
                        next_line = lines[i + 1]
                        perf_parts = [p.strip() for p in next_line.split('|')]

                        # Temperature, power information
                        temp_parts = perf_parts[1].split()
                        temp = temp_parts[1].replace('C', '')
                        power = temp_parts[4] if len(temp_parts) > 4 else 'N/A'

                        # Memory, utilization information
                        util_parts = perf_parts[2].split()
                        memory_used = util_parts[0]
                        memory_total = util_parts[2]
                        utilization = util_parts[-2] if len(util_parts) > 2 else 'N/A'

                        gpu = {
                            'id': gpu_id,
                            'name': 'TITAN RTX',
                            'temp': temp,
                            'power': power,
                            'memory_used': memory_used,
                            'memory_total': memory_total,
                            'utilization': utilization,
                            'processes': []
                        }
                        gpus.append(gpu)

                    except Exception as e:
                        print(f"GPU info parsing error: {str(e)}")
                        continue

            # Parse process information
            process_lines = []
            for i, line in enumerate(lines):
                if '| Processes:' in line:
                    in_process_section = True
                    continue
                if in_process_section and line.strip().startswith('|'):
                    if 'GPU   GI   CI' in line or '=' in line:
                        continue
                    if line.strip() != '|':
                        process_lines.append(line)

            # Process process information
            for line in process_lines:
                try:
                    parts = line.strip().split('|')
                    if len(parts) < 2:
                        continue

                    process_parts = parts[1].strip().split()
                    if len(process_parts) >= 5:  # Check if GPU ID, PID, Type, Process name, Memory info exist
                        gpu_id = process_parts[0]
                        pid = process_parts[3]
                        memory = process_parts[-1]

                        # Get detailed info using ps command
                        try:
                            stdin, stdout, stderr = ssh_client.exec_command(f'ps -f --no-headers -o user,pid,start_time,command -p {pid}') # Modified ps command to use 'start_time'
                            ps_output = stdout.read().decode()
                            ps_lines = ps_output.strip().split('\n')

                            if len(ps_lines) > 0:
                                ps_info = ps_lines[0].split() # Removed [1] index because of --no-headers
                                username = ps_info[0]
                                pid_ps = ps_info[1] # PID from ps command, should match nvidia-smi PID
                                start_time_str = ps_info[2] # Start time is now in YYYY format, using 'start_time' instead of 'lstart'

                                command = ' '.join(ps_info[3:])

                                # GPU start time is YYYY, try to get full start time using `lstart` if 'start_time' is just year
                                if len(start_time_str) == 4 and start_time_str.isdigit():
                                    stdin_lstart, stdout_lstart, stderr_lstart = ssh_client.exec_command(f'ps -f --no-headers -o lstart -p {pid}')
                                    lstart_output = stdout_lstart.read().decode().strip()
                                    if lstart_output:
                                        start_time_str = lstart_output # Use lstart if available for full time
                                    else:
                                        start_time_str = f"Year {start_time_str}" # Indicate year only if lstart fails


                                # Add process info to GPU
                                for gpu in gpus:
                                    if gpu['id'] == gpu_id:
                                        gpu['processes'].append({
                                            'pid': pid_ps, # Use PID from ps command for consistency
                                            'memory': memory,
                                            'user': username,
                                            'start_time': start_time_str, # Full start time string or Year
                                            'command': command
                                        })
                        except Exception as e:
                            print(f"Failed to retrieve process details (PID: {pid}): {str(e)}")
                            continue

                except Exception as e:
                    print(f"Process line parsing error: {str(e)}")
                    continue

            # Format result
            result = []
            header = f"+{'-' * 120}+"  # Increased width
            result.append(header)
            result.append(f"| {'GPU Status Information':^118} |") # Increased width
            result.append(header)

            for gpu in gpus:
                # GPU basic information
                result.append(f"| GPU {gpu['id']} | {gpu['name']} |")
                result.append(
                    f"| Temperature: {gpu['temp']}°C | "
                    f"Power: {gpu['power']} | "
                    f"Memory: {gpu['memory_used']}/{gpu['memory_total']} | "
                    f"Utilization: {gpu['utilization']} |"
                )
                result.append(f"|{'-' * 120}|") # Increased width

                # Process information
                if gpu['processes']:
                    result.append(f"| {'User(PID)':^20} | {'Start Time':^20} | {'Memory':^12} | {'Process':^63} |") # Combined User(PID), Increased Process width, Wider Start Time
                    result.append(f"|{'-' * 120}|") # Increased width
                    for proc in gpu['processes']:
                        command = proc['command']
                        if len(command) > 63: # Increased Process width
                            command = command[:60] + "..." # Increased Process width
                        user_pid = f"{proc['user']}({proc['pid']})" # Combined User and PID
                        result.append(
                            f"| {user_pid:<20} | {proc['start_time']:<20} | " # Combined User(PID), Wider Start Time
                            f"{proc['memory']:>12} | {command:<63} |" # Increased Process width
                        )
                else:
                    result.append(f"| {'No running processes':^118} |") # Increased width
                result.append(header)

            return '\n'.join(result)

        except Exception as e:
            return f"Error parsing GPU information: {str(e)}\nOriginal output:\n{output}"

    def update_gpu_status(self, server: Dict):
        try:
            # Display loading message with progress bar
            progress_bar = ft.ProgressBar(width=400, value=None) # Indeterminate progress bar
            loading_content = ft.Column(
                controls=[
                    ft.Text(f"Checking GPU Status for {server['name']}...", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("Please wait while fetching GPU information.",
                        size=14, color=ft.Colors.GREY_600),
                    ft.Container(height=20),
                    progress_bar,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            self.gpu_status_container.content = loading_content
            self.page.update()

            # SSH connection and get GPU info
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            username = self.username_field.value or self.config["credentials"]["default_username"]
            password = self.password_field.value or self.config["credentials"]["default_password"]

            try:
                ssh.connect(server["ip"], username=username, key_filename=os.path.expanduser('~/.ssh/id_rsa'))
            except Exception:
                ssh.connect(server["ip"], username=username, password=password)

            stdin, stdout, stderr = ssh.exec_command('nvidia-smi')
            gpu_output = stdout.read().decode()

            # GPU info parsing
            gpus = self.parse_gpu_info(gpu_output, ssh)

            # UI 구성
            content_column = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(f"{server['name']} Status", size=20, weight=ft.FontWeight.BOLD),
                            ft.Container(width=20),
                            ft.Text(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                                size=14, color=ft.Colors.GREY_600),
                        ],
                    ),
                    ft.Divider(height=1, color=ft.Colors.GREY_300),
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=20,
            )

            # Logic to arrange GPU cards in 2 columns
            gpu_rows = []
            for i in range(0, len(gpus), 2):
                row_gpus = gpus[i:i+2]
                gpu_cards = []

                for gpu in row_gpus:
                    # GPU basic information card
                    gpu_info = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(
                                    ft.Icons.MEMORY,
                                    color=self.get_temperature_color(float(gpu['temp'])),
                                    size=24
                                ),
                                ft.Text(
                                    f"GPU {gpu['id']} | {gpu['name']}",
                                    size=16,
                                    weight=ft.FontWeight.BOLD
                                ),
                            ]),
                            ft.Text(
                                f"Temperature: {gpu['temp']}°C | Power: {gpu['power']}",
                                size=12,
                            ),
                            ft.Text(
                                f"Memory: {gpu['memory_used']}/{gpu['memory_total']}",
                                size=12,
                            ),
                            ft.Text(
                                f"Utilization: {gpu['utilization']}",
                                size=12,
                            ),
                        ]),
                        padding=10,
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=10,
                    )

                    # Process information section
                    process_column = ft.Column(controls=[], spacing=5)

                    if gpu['processes']:
                        # Create header row for process info
                        header_row = ft.Row(
                            controls=[
                                ft.Text("User(PID)", size=12, width=120),
                                ft.Text("Start Time", size=12, width=120),
                                ft.Text("Memory", size=12, width=80),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        )
                        process_column.controls.append(header_row)

                        # Add basic process info rows (always visible)
                        for proc in gpu['processes']:
                            user_pid_display = f"{proc['user']}({proc['pid']})"
                            basic_info_row = ft.Row(
                                controls=[
                                    ft.Text(user_pid_display, size=12, width=120),
                                    ft.Text(proc['start_time'], size=12, width=120),
                                    ft.Text(proc['memory'], size=12, width=80),
                                ],
                                alignment=ft.MainAxisAlignment.START,
                            )
                            process_column.controls.append(basic_info_row)

                        # Add show details button and process commands (initially hidden)
                        show_details_button = ft.ElevatedButton(
                            "Show Process Details",
                            on_click=lambda e, processes=gpu['processes']: self.toggle_process_details(e, processes),
                        )
                        process_column.controls.append(show_details_button)

                        # Container for process commands (initially hidden)
                        process_details = ft.Column(
                            controls=[],
                            visible=False,
                        )

                        # Add process command information with full text
                        for proc in gpu['processes']:
                            command = proc['command']
                            # Create a container for the command with tooltip
                            command_container = ft.Container(
                                content=ft.Column([
                                    ft.Text(
                                        "Process:",
                                        size=12,
                                        color=ft.colors.GREY_700,
                                        weight=ft.FontWeight.BOLD
                                    ),
                                    ft.Text(
                                        command,
                                        size=12,
                                        color=ft.colors.GREY_700,
                                        width=350,
                                        selectable=True,  # Makes text selectable
                                        tooltip=command,  # Shows full text on hover
                                        text_align=ft.TextAlign.LEFT,
                                        no_wrap=False,   # Enables text wrapping
                                    )
                                ]),
                                padding=ft.padding.only(left=10, top=5, bottom=5),
                            )
                            process_details.controls.append(command_container)

                        process_column.controls.append(process_details)
                    else:
                        process_column.controls.append(
                            ft.Text(
                                "No running processes",
                                color=ft.Colors.GREY_600,
                                italic=True,
                                size=12,
                            )
                        )

                    # GPU card creation
                    gpu_card = ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                gpu_info,
                                ft.Divider(height=1, color=ft.Colors.GREY_300),
                                process_column,
                            ]),
                            padding=10,
                            width=380,
                        ),
                    )
                    gpu_cards.append(gpu_card)

                # Add GPU cards to Row
                gpu_row = ft.Row(
                    controls=gpu_cards,
                    alignment=ft.MainAxisAlignment.START,
                    spacing=20,
                )
                gpu_rows.append(gpu_row)

            # Add all GPU rows to content_column
            for row in gpu_rows:
                content_column.controls.append(row)

            self.gpu_status_container.content = content_column
            self.page.update()

            ssh.close()

        except Exception as e:
            self.show_error(f"Status check failed: {str(e)}")
            if 'ssh' in locals():
                ssh.close()


    def toggle_process_details(self, e, processes):
        """Toggle visibility of process command details"""
        button = e.control
        details_container = button.parent.controls[-1]  # Get the process details container
        is_visible = not details_container.visible
        
        details_container.visible = is_visible
        button.text = "Hide Process Details" if is_visible else "Show Process Details"
        self.page.update()



    def get_temperature_color(self, temp: float) -> str:
        """Returns color based on GPU temperature"""
        if temp >= 80:
            return ft.colors.RED
        elif temp >= 70:
            return ft.colors.ORANGE
        elif temp >= 60:
            return ft.colors.YELLOW
        else:
            return ft.colors.GREEN

    def parse_gpu_info(self, output: str, ssh_client: paramiko.SSHClient) -> list:
        """Parses nvidia-smi output and returns GPU information"""
        lines = output.split('\n')
        gpus = []
        in_process_section = False

        # GPU basic information parsing
        for i, line in enumerate(lines):
            if '|   ' in line and 'NVIDIA' in line:
                try:
                    parts = [p.strip() for p in line.split('|')]
                    gpu_info = parts[1].strip().split()
                    gpu_id = gpu_info[0]

                    next_line = lines[i + 1]
                    perf_parts = [p.strip() for p in next_line.split('|')]

                    temp_parts = perf_parts[1].split()
                    temp = temp_parts[1].replace('C', '')
                    power = temp_parts[4] if len(temp_parts) > 4 else 'N/A'

                    util_parts = perf_parts[2].split()
                    memory_used = util_parts[0]
                    memory_total = util_parts[2]
                    utilization = util_parts[-2] if len(util_parts) > 2 else 'N/A'

                    gpu = {
                        'id': gpu_id,
                        'name': 'TITAN RTX',
                        'temp': temp,
                        'power': power,
                        'memory_used': memory_used,
                        'memory_total': memory_total,
                        'utilization': utilization,
                        'processes': []
                    }
                    gpus.append(gpu)

                except Exception as e:
                    print(f"GPU info parsing error: {str(e)}")
                    continue

        # Process information parsing
        process_lines = []
        for i, line in enumerate(lines):
            if '| Processes:' in line:
                in_process_section = True
                continue
            if in_process_section and line.strip().startswith('|'):
                if 'GPU   GI   CI' in line or '=' in line:
                    continue
                if line.strip() != '|':
                    process_lines.append(line)

        # Process process information
        for line in process_lines:
            try:
                parts = line.strip().split('|')
                if len(parts) < 2:
                    continue

                process_parts = parts[1].strip().split()
                if len(process_parts) >= 5:
                    gpu_id = process_parts[0]
                    pid = process_parts[3]
                    memory = process_parts[-1]

                    try:
                        stdin, stdout, stderr = ssh_client.exec_command(f'ps -f --no-headers -o user,pid,start_time,command -p {pid}') # Modified ps command to use 'start_time'
                        ps_output = stdout.read().decode()
                        ps_lines = ps_output.strip().split('\n')

                        if len(ps_lines) > 0:
                            ps_info = ps_lines[0].split() # Removed [1] index because of --no-headers
                            username = ps_info[0]
                            pid_ps = ps_info[1] # PID from ps command
                            start_time_str = ps_info[2] # Start time is now in YYYY format, using 'start_time' instead of 'lstart'

                            command = ' '.join(ps_info[3:])

                            # GPU start time is YYYY, try to get full start time using `lstart` if 'start_time' is just year
                            if len(start_time_str) == 4 and start_time_str.isdigit():
                                stdin_lstart, stdout_lstart, stderr_lstart = ssh_client.exec_command(f'ps -f --no-headers -o lstart -p {pid}')
                                lstart_output = stdout_lstart.read().decode().strip()
                                if lstart_output:
                                    start_time_str = lstart_output # Use lstart if available for full time
                                else:
                                    start_time_str = f"Year {start_time_str}" # Indicate year only if lstart fails


                            for gpu in gpus:
                                if gpu['id'] == gpu_id:
                                    gpu['processes'].append({
                                        'pid': pid_ps, # Use PID from ps command for consistency
                                        'memory': memory,
                                        'user': username,
                                        'start_time': start_time_str, # Full start time string or Year
                                        'command': command
                                    })
                    except Exception as e:
                        print(f"Failed to retrieve process details (PID: {pid}): {str(e)}")
                        continue

            except Exception as e:
                print(f"Process line parsing error: {str(e)}")
                continue

        return gpus

    def highlight_process_info(self, output: str) -> str:
        # Add red highlight to process information
        # Example: Highlight GPU process list in red
        highlighted = output.replace("Processes", "<span style='color:red;'>Processes</span>")
        # Here, "Processes" part is shown as red as an example.
        # You need to find the part corresponding to actual GPU process info and style that part.
        return highlighted

    def connect_to_server(self, server: Dict):
        username = self.username_field.value or self.config["credentials"]["default_username"]
        password = self.password_field.value or self.config["credentials"]["default_password"]

        try:
            # SSH connection settings
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Display SSH connection attempt
            self.show_snackbar(f"Connecting to {server['name']}...")

            # SSH key path
            ssh_key_path = os.path.expanduser('~/.ssh/id_rsa')

            # Attempt SSH connection (try key authentication first, then password if failed)
            try:
                ssh.connect(server["ip"], username=username, key_filename=ssh_key_path)
            except Exception as key_error:
                ssh.connect(server["ip"], username=username, password=password)

            # Execute 1111 command
            stdin, stdout, stderr = ssh.exec_command("1111")

            # Find VS Code path
            vscode_paths = [
                # Windows paths
                r"C:\Program Files\Microsoft VS Code\Code.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
                # Mac path
                "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"
            ]

            vscode_path = None
            for path in vscode_paths:
                if os.path.exists(path):
                    vscode_path = path
                    break

            if vscode_path:
                subprocess.Popen([
                    vscode_path,
                    "--remote",
                    f"ssh-remote+{username}@{server['ip']}",
                    f"/home/{username}"
                ])
                self.show_snackbar(f"Successfully connected to {server['name']}!", color="green")
            else:
                self.show_error("VS Code is not installed or cannot be found in the default paths.")

            ssh.close()

        except Exception as e:
            self.show_error(f"Connection failed: {str(e)}")

    def show_error(self, message: str):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED_400,
            action="OK"
        )
        self.page.snack_bar.open = True
        self.page.update()

    def show_snackbar(self, message: str, color="blue"):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.BLUE_400 if color == "blue" else ft.Colors.GREEN_400,
            action="OK"
        )
        self.page.snack_bar.open = True
        self.page.update()

def main(page: ft.Page):
    SSHConnector(page)

if __name__ == "__main__":
    ft.app(target=main)