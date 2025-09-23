import os, smtplib, time, re, ssl, glob
from email.message import EmailMessage

# Procurar nos possíveis locais
def find_log_file():
    possible_paths = [
        "/logs/onedrive.log",
        "/logs/*.log",
        "/var/log/onedrive/*.log"
    ]
    
    for pattern in possible_paths:
        files = glob.glob(pattern)
        if files:
            newest = max(files, key=os.path.getmtime)
            print(f"Encontrado arquivo de log: {newest}")
            return newest
    
    # Se não encontrar, usa o padrão
    print("Nenhum arquivo de log encontrado, usando padrão")
    return "/logs/onedrive.log"

LOG_FILE = find_log_file()
pattern = re.compile(r"error", re.IGNORECASE)  # Mais permissivo
cooldown = int(os.getenv("COOLDOWN_SECONDS", "300"))
last_sent_ts = 0
smtp_host = os.getenv("SMTP_HOST")
smtp_port = int(os.getenv("SMTP_PORT", "465"))  # Corrigido para 465
smtp_user = os.getenv("SMTP_USER")
smtp_pass = os.getenv("SMTP_PASS")
mail_from = os.getenv("MAIL_FROM", smtp_user)
mail_to = os.getenv("MAIL_TO")
subject_prefix = os.getenv("SUBJECT_PREFIX", "[OneDrive ERROR]")

def send_mail(lines):
    global last_sent_ts
    if not (smtp_host and mail_to and lines):
        print(f"Faltando configuração: host={smtp_host}, to={mail_to}, linhas={len(lines)}")
        return
    
    print(f"Enviando email com {len(lines)} linhas para {mail_to}")
    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = f"{subject_prefix} {time.strftime('%Y-%m-%d %H:%M:%S')}"
    msg.set_content("Linhas com 'error':\n\n" + "\n".join(lines[-20:]))
    
    try:
        # Usando SMTP_SSL para porta 465
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30) as s:
            if smtp_user and smtp_pass:
                s.login(smtp_user, smtp_pass)
            s.send_message(msg)
        last_sent_ts = time.time()
        print("Email enviado com sucesso")
    except Exception as e:
        print(f"Erro ao enviar email: {e}")

def tail(file_path):
    check_count = 0
    # Verifique tamanho do arquivo
    if os.path.exists(file_path) and os.path.getsize(file_path) > 100_000_000:  # 100MB
        print(f"Arquivo muito grande, rotacionando: {file_path}")
        backup = f"{file_path}.1"
        if os.path.exists(backup):
            os.remove(backup)
        os.rename(file_path, backup)
        
        # Crie arquivo vazio com permissões abertas
        with open(file_path, "w") as f:
            f.write("# Log file rotated by watcher.py\n")
        # Aplica permissões 666 (escrita para todos)
        os.chmod(file_path, 0o666)
        print(f"Novo arquivo criado com permissões 666")
    
    print(f"Iniciando monitoramento de: {file_path}")
    
    # Criar arquivo vazio se não existir
    if not os.path.exists(file_path):
        print(f"Arquivo não existe, criando: {file_path}")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write("# Log file initialized by watcher.py\n")
        # Aplica permissões 666 (escrita para todos)
        os.chmod(file_path, 0o666)
        print(f"Arquivo inicializado com permissões 666")
    
    with open(file_path, "r", errors="ignore") as f:
        # Iniciar do final
        f.seek(0, 2)
        buffer = []
        print("Monitorando novas linhas...")
        
        while True:
            # Verificar tamanho periodicamente
            check_count += 1
            if check_count >= 1000:  # A cada 1000 iterações
                if os.path.getsize(file_path) > 100_000_000:  # 100MB
                    # Rotacionar arquivo
                    print(f"Arquivo muito grande, rotacionando: {file_path}")
                    backup = f"{file_path}.1"
                    if os.path.exists(backup):
                        os.remove(backup)
                    os.rename(file_path, backup)
                    
                    # Crie arquivo vazio com permissões abertas
                    with open(file_path, "w") as f:
                        f.write("# Log file rotated by watcher.py\n")
                    # Aplica permissões 666 (escrita para todos)
                    os.chmod(file_path, 0o666)
                    print(f"Novo arquivo criado com permissões 666")
                    
                    return  # Força reinício do tail com novo arquivo
                
                check_count = 0
            
            line = f.readline()
            if line:
                print(f"Nova linha: {line.strip()}")
                if pattern.search(line):
                    print(f"⚠️ Erro encontrado: {line.strip()}")
                    buffer.append(line.strip())
                    if time.time() - last_sent_ts >= cooldown:
                        send_mail(buffer)
                        buffer.clear()
            else:
                time.sleep(0.5)
            
            # Limpa buffer gigante se cooldown longo
            if len(buffer) > 2000:
                buffer = buffer[-500:]

if __name__ == "__main__":
    print("Iniciando watcher.py")
    print(f"Configuração: SMTP={smtp_host}:{smtp_port}, From={mail_from}, To={mail_to}")
    
    while True:
        try:
            tail(LOG_FILE)
        except Exception as e:
            print(f"⚠️ Erro no watcher: {e}")
            time.sleep(10)

