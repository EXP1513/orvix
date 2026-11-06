import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÕES DO GOOGLE SHEETS ---
NOME_PLANILHA = "ORVIX- MONITOR"
NOME_ABA = "ATUAL"

def atualizar_google_sheets(dados):
    # Carrega as credenciais a partir do Secret do GitHub
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise ValueError("A variável GOOGLE_SERVICE_ACCOUNT_JSON não foi encontrada nos Secrets.")
    
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    
    client = gspread.authorize(credentials)
    sheet = client.open(NOME_PLANILHA).worksheet(NOME_ABA)
    
    # Limpa a aba antes de escrever os novos dados
    sheet.clear()
    
    if dados:
        sheet.update("A1", dados)
        print(f"Planilha atualizada com sucesso na aba '{NOME_ABA}'!")
    else:
        print("Nenhum dado encontrado para atualizar.")

# --- AUTOMAÇÃO COM PLAYWRIGHT ---
def executar_bot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Acessando a tela de login...")
        page.goto("https://atendimento.redeservice.com.br/administrador/login.aspx")
        page.wait_for_load_state("networkidle")

        # Preenchimento das credenciais de acesso
        print("Preenchendo usuário e senha...")
        page.fill('input[name*="Usuario"], input[name*="txtUsuario"], input[id*="Usuario"], input[type="text"]', "expedito.luiz@gruporenac.com.br")
        page.fill('input[type="password"]', "@626311Ab")

        # Clique no botão Entrar
        print("Clicando no botão Entrar...")
        page.click('input[type="submit"], button[type="submit"], input[value*="Entrar"], button:has-text("Entrar")')
        page.wait_for_load_state("networkidle")

        # Acesso à página do relatório
        print("Acessando a página de pesquisa...")
        page.goto("https://atendimento.redeservice.com.br/administrador/sala_pesquisar.aspx")
        page.wait_for_load_state("networkidle")

        # Configuração das datas e horários (Data atual e 00:00 - 23:59)
        hoje = datetime.now().strftime("%d/%m/%Y")
        print(f"Aplicando filtros para a data: {hoje}...")

        inputs_texto = page.locator('input[type="text"]').all()
        if len(inputs_texto) >= 2:
            inputs_texto[0].fill(hoje)
            inputs_texto[1].fill(hoje)

        inputs_hora = page.locator('input[name*="hora"], input[id*="hora"]').all()
        if len(inputs_hora) >= 2:
            inputs_hora[0].fill("00:00")
            inputs_hora[1].fill("23:59")

        # Execução da pesquisa
        print("Filtrando relatório...")
        page.click('input[type="submit"], button:has-text("Pesquisar"), button:has-text("Buscar")')
        page.wait_for_load_state("networkidle")

        # Extração dos dados da tabela
        print("Extraindo dados da tabela...")
        rows = page.locator("table tr").all()
        dados_tabela = []

        for row in rows:
            cols = row.locator("td, th").all_text_contents()
            cols_limpas = [c.strip() for c in cols]
            if any(cols_limpas):
                dados_tabela.append(cols_limpas)

        browser.close()
        return dados_tabela

if __name__ == "__main__":
    print("Iniciando a execução da automação...")
    dados = executar_bot()
    atualizar_google_sheets(dados)
