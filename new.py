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
        self.setup_icons()  # 아이콘 설정 추가
        self.create_ui()

    def load_config(self) -> Dict:
        try:
            with open('servers.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.show_error("servers.json 파일을 찾을 수 없습니다.")
            return {"credentials": {"default_username": "", "default_password": ""}, "servers": []}
        
        
    def setup_icons(self):
        """아이콘 관련 deprecated 경고 수정을 위한 메서드"""
        self.person_icon = ft.Icons.PERSON
        self.lock_icon = ft.Icons.LOCK
        
    def create_ui(self):
        # 왼쪽 패널 (서버 목록)
        left_panel = self.create_left_panel()
        

        # 상단 버튼 패널 추가
        top_panel = ft.Row(
            controls=[
                ft.ElevatedButton(
                    "모든 GPU 상태 확인",
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.BLUE,
                    on_click=self.handle_check_all_gpu_status,
                ),
                ft.ElevatedButton(
                    "Linux 사용 매뉴얼",
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.GREEN,
                    on_click=self.handle_open_manual,
                ),
                ft.ElevatedButton(
                    "장기사용 신청",
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.ORANGE,
                    on_click=self.handle_open_longterm,
                ),
            ],
            alignment=ft.MainAxisAlignment.END,
            spacing=10,  # 버튼 사이 간격
        )
        
        # 오른쪽 패널 (GPU 상태)
        self.gpu_status_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("GPU 상태", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("서버를 선택하여 GPU 상태를 확인하세요", 
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

        # 전체 레이아웃
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
        """GPU 현황 확인 버튼 핸들러 - 웹사이트로 리다이렉션"""
        import webbrowser
        webbrowser.open('http://10.201.135.113:8890')

    def handle_open_manual(self, e):
        """Linux 사용 매뉴얼 버튼 핸들러"""
        import webbrowser
        webbrowser.open('https://dashlab-manual.netlify.app')

    def handle_open_longterm(self, e):
        """장기사용 신청 엑셀 링크 버튼 핸들러"""
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
            
            # 프로그레스 표시 UI 생성
            progress_bar = ft.ProgressBar(width=400, value=0)
            progress_text = ft.Text("서버 연결 준비 중...", size=14, color=ft.colors.GREY_600)
            server_status_text = ft.Text("", size=14, color=ft.colors.GREY_600)
            
            loading_content = ft.Column(
                controls=[
                    ft.Text("모든 GPU 상태 로딩 중...", size=20, weight=ft.FontWeight.BOLD),
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

            # 모든 서버의 상태 정보를 저장할 리스트
            all_status = []

            # 각 서버에 대해 상태 확인
            for server in self.config["servers"]:
                current_server += 1
                progress = current_server / total_servers
                
                # 프로그레스 업데이트
                progress_bar.value = progress
                progress_text.value = f"진행 상황: {current_server}/{total_servers} ({int(progress * 100)}%)"
                server_status_text.value = f"현재 서버: {server['name']} ({server['ip']})"
                self.page.update()

                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    username = self.username_field.value or self.config["credentials"]["default_username"]
                    password = self.password_field.value or self.config["credentials"]["default_password"]
                    
                    server_status_text.value = f"'{server['name']}' 연결 중..."
                    self.page.update()
                    
                    try:
                        ssh_key_path = os.path.expanduser('~/.ssh/id_rsa')
                        ssh.connect(server["ip"], username=username, key_filename=ssh_key_path)
                    except Exception:
                        ssh.connect(server["ip"], username=username, password=password)

                    server_status_text.value = f"'{server['name']}' GPU 정보 수집 중..."
                    self.page.update()
                    
                    stdin, stdout, stderr = ssh.exec_command('nvidia-smi')
                    output = stdout.read().decode()
                    
                    all_status.append({
                        "server_name": server["name"],
                        "status": self.format_gpu_info(output)
                    })
                    
                    ssh.close()
                    
                except Exception as e:
                    all_status.append({
                        "server_name": server["name"],
                        "status": f"연결 실패: {str(e)}"
                    })

            # 프로그레스 완료 표시
            progress_text.value = "모든 서버 정보 수집 완료!"
            server_status_text.value = "결과 생성 중..."
            self.page.update()

            # 전체 상태 정보를 하나의 문자열로 결합
            combined_status = "\n\n".join([
                f"=== {status['server_name']} ===\n{status['status']}"
                for status in all_status
            ])

            # 최종 UI 업데이트
            status_content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("전체 GPU 상태", size=20, weight=ft.FontWeight.BOLD),
                            ft.Container(width=20),
                            ft.Text(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
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
            self.show_error(f"GPU 상태 확인 실패: {str(e)}")

    def create_left_panel(self):
        # Credentials Section
        self.username_field = ft.TextField(
            label="Username",
            prefix_icon=ft.icons.PERSON,
            border_radius=10,
            value=self.config["credentials"]["default_username"],
            width=250,
        )
        self.password_field = ft.TextField(
            label="Password",
            prefix_icon=ft.icons.LOCK,
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

        # 서버 목록
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
                    ft.Text("서버 목록", size=16, weight=ft.FontWeight.BOLD),
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
                                    "연결",
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.BLUE,
                                    on_click=lambda e, s=server: self.connect_to_server(s),
                                ),
                                ft.ElevatedButton(
                                    "GPU 상태",
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
        

    def update_gpu_status(self, server: Dict):
        try:
            # 로딩 중 메시지 표시
            loading_content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("서버 정보 로딩 중...", size=20, weight=ft.FontWeight.BOLD),
                            ft.Container(width=20),
                            ft.Text("정보 업데이트 중입니다. 잠시만 기다려주세요.", size=14, color=ft.colors.GREY_600),
                        ],
                    ),
                ],
            )
            self.gpu_status_container.content = loading_content
            self.page.update()

            # SSH 연결
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            username = self.username_field.value or self.config["credentials"]["default_username"]
            password = self.password_field.value or self.config["credentials"]["default_password"]
            
            try:
                ssh.connect(server["ip"], username=username, key_filename=os.path.expanduser('~/.ssh/id_rsa'))
            except Exception:
                ssh.connect(server["ip"], username=username, password=password)

            # 사용자 정보 얻기
            stdin, stdout, stderr = ssh.exec_command('w -h')  # -h 옵션은 헤더를 제외
            users_output = stdout.read().decode()
            
            # GPU 정보 얻기
            stdin, stdout, stderr = ssh.exec_command('nvidia-smi')
            gpu_output = stdout.read().decode()

            # 출력 포맷팅
            formatted_gpu = self.format_gpu_info(gpu_output)
            formatted_users = self.format_user_info(users_output)

            # 상태 정보 업데이트
            status_content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(f"{server['name']} 상태", size=20, weight=ft.FontWeight.BOLD),
                            ft.Container(width=20),
                            ft.Text(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                size=14, color=ft.colors.GREY_600),
                        ],
                    ),
                    ft.Divider(height=1, color=ft.colors.GREY_300),
                    # 사용자 정보 표시
                    ft.Container(
                        content=ft.Column([
                            ft.Text("현재 접속 중인 사용자", size=16, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Text(formatted_users, 
                                            size=14, 
                                            font_family="Consolas",
                                            selectable=True),
                                bgcolor=ft.colors.GREY_50,
                                padding=10,
                                border_radius=5,
                            ),
                        ]),
                        margin=ft.margin.only(bottom=20),
                    ),
                    # GPU 정보 표시
                    ft.Container(
                        content=ft.Column([
                            ft.Text("GPU 상태", size=16, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Text(formatted_gpu, 
                                            size=14, 
                                            font_family="Consolas",
                                            selectable=True),
                                bgcolor=ft.colors.GREY_50,
                                padding=10,
                                border_radius=5,
                            ),
                        ]),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            )

            self.gpu_status_container.content = status_content
            self.page.update()

            ssh.close()
            
        except Exception as e:
            self.show_error(f"상태 확인 실패: {str(e)}")
            
    def format_user_info(self, output: str) -> str:
        """사용자 정보를 포맷팅"""
        if not output.strip():
            return "현재 접속 중인 사용자가 없습니다."
            
        lines = output.strip().split('\n')
        
        # 테이블 설정
        table_width = 75
        user_width = 15
        tty_width = 10
        from_width = 20
        login_width = 15
        what_width = table_width - user_width - tty_width - from_width - login_width - 9  # 구분자 여백
        
        # 테이블 생성
        border = "+" + "-" * table_width + "+"
        header = f"| {'사용자':^{user_width}} | {'TTY':^{tty_width}} | {'접속위치':^{from_width}} | {'로그인시간':^{login_width}} | {'작업':^{what_width}} |"
        
        formatted_output = [
            border,
            header,
            border
        ]
        
        # 사용자 정보 추가
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

    def format_gpu_info(self, output: str) -> str:
        """nvidia-smi 출력을 파싱하여 정돈된 형식으로 변환"""
        lines = output.split('\n')
        
        # GPU 개수 카운트
        gpu_count = sum(1 for line in lines if 'NVIDIA' in line and 'On' in line)
        
        # 프로세스 정보 파싱
        processes = []
        is_process_section = False
        
        for line in lines:
            if 'Processes' in line:
                is_process_section = True
                continue
                
            if is_process_section and line.strip():
                if 'GPU   GI   CI' in line or '=' in line or not line.strip('| '):
                    continue
                    
                content = line.strip('| \n')
                if content:
                    parts = ' '.join(content.split()).split()
                    
                    if len(parts) >= 7:
                        process = {
                            'gpu': parts[0],
                            'pid': parts[3],
                            'type': parts[4],
                            'name': parts[5],
                            'memory': parts[-1]
                        }
                        processes.append(process)
        
        # 테이블 너비 설정
        table_width = 75
        gpu_width = 4
        pid_width = 8
        type_width = 6
        memory_width = 12
        name_width = table_width - gpu_width - pid_width - type_width - memory_width - 9  # 구분자 여백 고려
        
        # 포맷된 출력 생성
        border = "+" + "-" * table_width + "+"
        formatted_output = [
            border,
            f"| 총 GPU 수: {gpu_count}{' ' * (table_width - len(str(gpu_count)) - 10)}|",
            border,
            "| GPU 프로세스 정보:",
            "+" + "=" * table_width + "+",
            f"| {'GPU':^{gpu_width}} | {'PID':^{pid_width}} | {'Type':^{type_width}} | {'Process Name':^{name_width}} | {'Memory':^{memory_width}} |",
            border
        ]
        
        # 프로세스 정보 추가
        for proc in processes:
            name = proc['name']
            if len(name) > name_width:
                name = "..." + name[-(name_width-3):]  # 긴 이름은 뒷부분만 표시
            
            line = (f"| {proc['gpu']:^{gpu_width}} "
                    f"| {proc['pid']:^{pid_width}} "
                    f"| {proc['type']:^{type_width}} "
                    f"| {name:<{name_width}} "
                    f"| {proc['memory']:>{memory_width}} |")
            formatted_output.append(line)
        
        if not processes:
            empty_msg = "실행 중인 프로세스 없음"
            formatted_output.append(f"| {empty_msg:^{table_width}} |")
        
        formatted_output.append(border)
        return '\n'.join(formatted_output)


    def highlight_process_info(self, output: str) -> str:
        # 프로세스 정보에 빨간색 하이라이트 추가
        # 예시: GPU 프로세스 목록을 빨간색으로 하이라이트 처리
        highlighted = output.replace("Processes", "<span style='color:red;'>Processes</span>")
        # 여기서 "Processes" 부분을 예시로 빨간색으로 표시했습니다.
        # 실제 GPU 프로세스 정보에 맞는 부분을 찾아서 해당 부분을 스타일링해야 합니다.
        return highlighted

    def connect_to_server(self, server: Dict):
        username = self.username_field.value or self.config["credentials"]["default_username"]
        password = self.password_field.value or self.config["credentials"]["default_password"]

        try:
            # SSH 연결 설정
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # SSH 연결 시도 중임을 표시
            self.show_snackbar(f"{server['name']}에 연결 중...")
            
            # SSH 키 경로
            ssh_key_path = os.path.expanduser('~/.ssh/id_rsa')
            
            # SSH 연결 시도 (먼저 키 인증 시도, 실패시 비밀번호 사용)
            try:
                ssh.connect(server["ip"], username=username, key_filename=ssh_key_path)
            except Exception as key_error:
                ssh.connect(server["ip"], username=username, password=password)
            
            # 1111 명령어 실행
            stdin, stdout, stderr = ssh.exec_command("1111")
            
            # VS Code 경로 찾기
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
                self.show_snackbar(f"{server['name']}에 성공적으로 연결되었습니다!", color="green")
            else:
                self.show_error("VS Code가 설치되어 있지 않거나 기본 경로에서 찾을 수 없습니다.")
            
            ssh.close()
            
        except Exception as e:
            self.show_error(f"연결 실패: {str(e)}")

    def show_error(self, message: str):
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.colors.RED_400,
                action="확인"
            )
        )

    def show_snackbar(self, message: str, color="blue"):
        self.page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.colors.BLUE_400 if color == "blue" else ft.colors.GREEN_400,
                action="확인"
            )
        )

def main(page: ft.Page):
    SSHConnector(page)

if __name__ == "__main__":
    ft.app(target=main)