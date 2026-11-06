import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAÇÕES ---
NOME_PLANILHA = "ORVIX- MONITOR"
NOME_ABA = "ATUAL"
URL_LOGIN = "https://atendimento.redeservice.com.br/administrador/login.aspx"
URL_PESQUISA = "https://atendimento.redeservice.com.br/administrador/sala_pesquisar.aspx"

USER_LOGIN = "expedito.luiz@gruporenac.com.br"
USER_SENHA = "@626311Ab"

def atualizar_google_sheets(dados):
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise ValueError("A variável GOOGLE_SERVICE_ACCOUNT_JSON não foi encontrada nos Secrets.")
    
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    
    client = gspread.authorize(credentials)
    sheet = client.open(NOME_PLANILHA).worksheet(NOME_ABA)
    
    sheet.clear()
    
    if dados:
        sheet.update("A1", dados)
        print(f"Planilha atualizada com sucesso na aba '{NOME_ABA}'!")
    else:
        print("Nenhum dado encontrado para atualizar.")

def extrair_relatorio_orvyx():
    hoje = datetime.now().strftime("%d/%m/%Y")
    print(f"--- Iniciando extração em {hoje} para a página sala_pesquisar.aspx ---")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Navegando para: {URL_LOGIN}")
        page.goto(URL_LOGIN)
        page.wait_for_load_state("networkidle")

        print("Página de login detectada. Preenchendo credenciais...")
        # Seleciona de forma genérica o campo de texto de login e a senha
        page.locator('input[type="text"]').first.fill(USER_LOGIN)
        page.locator('input[type="password"]').first.fill(USER_SENHA)

        print("Clicando no botão de entrar...")
        # Clica no botão de submissão do formulário de login
        page.locator('input[type="submit"], button[type="submit"], input[value*="Entrar"], button:has-text("Entrar")').first.click()
        page.wait_for_load_state("networkidle")

        print(f"Navegando para a página de relatórios: {URL_PESQUISA}")
        page.goto(URL_PESQUISA)
        page.wait_for_load_state("networkidle")

        print(f"Aplicando filtros de data para: {hoje} e horário 00:00 - 23:59...")
        inputs_texto = page.locator('input[type="text"]').all()
        if len(inputs_texto) >= 2:
            inputs_texto[0].fill(hoje)
            inputs_texto[1].fill(hoje)

        inputs_hora = page.locator('input[name*="hora"], input[id*="hora"]').all()
        if len(inputs_hora) >= 2:
            inputs_hora[0].fill("00:00")
            inputs_hora[1].fill("23:59")

        print("Executando a pesquisa...")
        page.locator('input[type="submit"], button:has-text("Pesquisar"), button:has-text("Buscar")').first.click()
        page.wait_for_load_state("networkidle")

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
    dados = extrair_relatorio_orvyx()
    atualizar_google_sheets(dados)
