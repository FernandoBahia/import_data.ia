# Importação de bibliotecas necessárias
import pandas as pd  # Para manipulação de dados em formato de tabela
import psycopg2  # Para conexão com banco de dados PostgreSQL
import os  # Para operações com arquivos e diretórios
import json  # Para trabalhar com arquivos JSON
import fitz  # Biblioteca PyMuPDF para ler PDFs
import docx  # Para ler arquivos Word (.docx)
from datetime import datetime  # Para registrar data/hora atual
import logging  # Para registrar mensagens do processo

# Configuração do sistema de logs (registros de execução)
logging.basicConfig(
    level=logging.INFO,  # Nível de detalhe (INFO mostra mensagens importantes)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Formato das mensagens
    handlers=[
        logging.FileHandler('import_script.log'),  # Salva logs em arquivo
        logging.StreamHandler()  # Mostra logs no terminal
    ]
)

def get_db_connection():
    """
    Cria e retorna uma conexão com o banco de dados PostgreSQL
    Configurado para conectar no servidor 172.23.1.50, banco 'dbsys'
    usando o usuário 'pgadmin' e senha 'P94dm1nP4s5'
    """
    try:
        # Tenta estabelecer a conexão com os parâmetros fornecidos
        conn = psycopg2.connect(
            host="172.23.1.50",  # Endereço do servidor PostgreSQL
            dbname="dbsys",  # Nome do banco de dados
            user="pgadmin",  # Nome de usuário 
            password="P94dm1nP4s5",  # Senha do banco
            client_encoding='utf-8'  # Codificação de caracteres
        )
        logging.info("Conexão com o banco de dados estabelecida com sucesso")
        return conn
    except psycopg2.Error as e:
        # Se houver erro na conexão, registra e interrompe
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        raise  # Recria a exceção para ser tratada posteriormente

def process_file(file_path, filename):
    """
    Processa um arquivo individual baseado em seu tipo/extensão
    Retorna um DataFrame pandas com:
    - titulo: nome do arquivo
    - conteudo: texto extraído
    - data_criacao: data/hora atual
    """
    try:
        # Processa cada tipo de arquivo de forma diferente
        if filename.endswith(('.xlsx', '.xls')):  # Arquivos Excel
            df = pd.read_excel(file_path, engine='openpyxl')
        elif filename.endswith('.csv'):  # Arquivos CSV
            df = pd.read_csv(file_path)
        elif filename.endswith('.json'):  # Arquivos JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                df = pd.json_normalize(data)  # Converte JSON para tabela
        elif filename.endswith('.txt'):  # Arquivos de texto simples
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Cria DataFrame com os metadados
                df = pd.DataFrame([{
                    'titulo': filename,
                    'conteudo': content,
                    'data_criacao': datetime.now()
                }])
        elif filename.endswith('.pdf'):  # Arquivos PDF
            doc = fitz.open(file_path)
            content = ""
            for page in doc:  # Extrai texto de cada página
                content += page.get_text()
            df = pd.DataFrame([{
                'titulo': filename,
                'conteudo': content,
                'data_criacao': datetime.now()
            }])
        elif filename.endswith('.docx'):  # Arquivos Word
            doc = docx.Document(file_path)
            # Junta todos os parágrafos em uma única string
            content = "\n".join([para.text for para in doc.paragraphs])
            df = pd.DataFrame([{
                'titulo': filename,
                'conteudo': content,
                'data_criacao': datetime.now()
            }])
        elif filename.endswith(('.mp4', '.bat', '.exe')):  # Arquivos binários
            # Apenas registra a existência, sem extrair conteúdo
            df = pd.DataFrame([{
                'titulo': filename,
                'conteudo': f"Arquivo binário: {filename}",
                'data_criacao': datetime.now()
            }])
        else:  # Tipos de arquivo não suportados
            logging.warning(f"Tipo de arquivo não suportado: {filename}")
            return None

        # Garante que todas as colunas necessárias existam
        if 'data_criacao' not in df.columns:
            df['data_criacao'] = datetime.now()
        if 'conteudo' not in df.columns:
            # Se não tiver conteúdo, converte toda a tabela para JSON
            df['conteudo'] = df.to_json(orient='records')
        
        return df  # Retorna os dados processados

    except Exception as e:  # Se der erro em qualquer processamento
        logging.error(f"Erro ao processar arquivo {filename}: {e}")
        return None  # Retorna vazio para continuar com próximo arquivo

def insert_data(conn, df, filename):
    """
    Insere os dados processados no banco de dados PostgreSQL
    na tabela 'base_conhecimento'
    """
    try:
        with conn.cursor() as cur:  # Cria um cursor para executar comandos SQL
            # Para cada linha do DataFrame (normalmente 1 por arquivo)
            for _, row in df.iterrows():
                # Verifica se o arquivo já foi importado antes
                cur.execute(
                    "SELECT COUNT(*) FROM base_conhecimento WHERE titulo = %s",
                    (row['titulo'],)
                )
                if cur.fetchone()[0] == 0:  # Se não existir
                    # Insere os dados na tabela
                    cur.execute(
                        """INSERT INTO base_conhecimento 
                        (titulo, conteudo, data_criacao) 
                        VALUES (%s, %s, %s)""",
                        (row['titulo'], row['conteudo'], row['data_criacao'])
                    )
            conn.commit()  # Confirma as alterações no banco
        logging.info(f"Dados do arquivo {filename} inseridos com sucesso")
    except Exception as e:  # Se der erro na inserção
        conn.rollback()  # Desfaz alterações não confirmadas
        logging.error(f"Erro ao inserir dados do arquivo {filename}: {e}")

def import_files_to_database(input_dir):
    """
    Função principal que orquestra todo o processo:
    1. Conecta ao banco
    2. Percorre todos os arquivos no diretório
    3. Processa cada arquivo
    4. Insere no banco
    """
    conn = None  # Inicializa a conexão como vazia
    try:
        conn = get_db_connection()  # Estabelece conexão com o banco
        
        # Percorre todas as pastas e arquivos no diretório fornecido
        for root, _, files in os.walk(input_dir):
            for filename in files:
                file_path = os.path.join(root, filename)  # Caminho completo
                logging.info(f"Processando arquivo: {file_path}")
                
                # Processa o arquivo e obtém os dados
                df = process_file(file_path, filename)
                if df is not None:  # Se foi processado com sucesso
                    insert_data(conn, df, filename)  # Insere no banco
                    
    except Exception as e:  # Se ocorrer erro geral
        logging.error(f"Erro durante a importação: {e}")
    finally:  # Sempre executa, mesmo com erro
        if conn is not None:  # Se a conexão existe
            conn.close()  # Fecha a conexão
            logging.info("Conexão com o banco de dados fechada")

if __name__ == "__main__":
    """
    Ponto de entrada do script quando executado diretamente
    """
    # Pasta onde os arquivos estão armazenados
    input_dir = r'C:\Users\fernando.bahia\Downloads\Base Conhecimento TI Multisaas - Base de Conhecimento'
    
    # Verifica se o diretório existe antes de começar
    if not os.path.exists(input_dir):
        logging.error(f"Diretório não encontrado: {input_dir}")
    else:
        logging.info(f"Iniciando importação de arquivos de: {input_dir}")
        import_files_to_database(input_dir)  # Inicia o processo principal
        logging.info("Processo de importação concluído")