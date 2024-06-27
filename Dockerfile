# Use a imagem base do Ubuntu
FROM ubuntu:latest

# Instale as dependências necessárias
RUN apt-get update && \
  apt-get install -y \
  sudo \
  wget \
  git \
  build-essential \
  libcurl4-openssl-dev \
  libsqlite3-dev \
  pkg-config \
  cmake \
  libgcrypt20-dev \
  libgnutls28-dev \
  libssl-dev \
  curl

#Para o OneDrive 
RUN apt install ldc -y

# Adicionar ldc2 ao PATH
# ENV PATH="/dlang/ldc2/bin:${PATH}"

# Clone o repositório do OneDrive
RUN git clone https://github.com/abraunegg/onedrive.git /onedrive

# Adicionar ldc2 ao PATH

# Compile e instale o OneDrive
RUN cd /onedrive && \
  ./configure && \
  make && \
  make install

# Configure um usuário não-root para executar o OneDrive
RUN useradd -m opera && \
  usermod -aG sudo opera

# Cria um grupo smbserver
RUN groupadd smbserver
# Adiciona o usuário opera ao grupo smbserver
RUN usermod -aG smbserver opera
# Instala o samba server
RUN apt-get install -y samba
# Adiciona o usuário opera ao samba
RUN (echo "opera228"; echo "opera228") | smbpasswd -a opera
# Cria um diretório para o hd
RUN mkdir -p /home/opera/hd
# Altera o dono do diretório
RUN chown opera:smbserver /home/opera/hd
# Altera as permissões do diretório
RUN chmod 775 /home/opera/hd