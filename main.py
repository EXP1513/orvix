import os
import json
from datetime import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

URL_PAINEL = "https://atendimento.redeservice.com.br/administrador/sala_pesquisar.aspx"
SPREADSHEET_ID = "1Vi4c-w36lLMkJA4LzQkVRPbcHdSxT1DsxO-OtKOrIsU"
NOME_ABA = "ATUAL"  # Aba específica onde os dados serão substituídos

# Credenciais de acesso ao sistema
USER_LOGIN = "expedito.luiz@gruporenac.com.br"
USER_PASS = "@626311Ab"

def extrair_relatorio_orvyx():
    hoje = datetime.now().strftime("%d/%m/%Y")
    hora_inicio = "00:00"
    hora_fim = "23:59"

    print(f"--- Iniciando extração em {hoje} para a página sala_pesquisar.aspx ---")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Navegando para: {URL_PAINEL}")
        page.goto(URL_PAINEL)

        # 1. Realizar Login caso seja solicitada autenticação
        if "login" in page.url.lower() or page.locator("input[type='password']").is_visible():
            print("Página de login detectada. Autenticando...")
            page.fill('input[name*="txtLogin"], input[name*="user"], input[id*="Login"]', USER_LOGIN)
            page.fill('input[name*="txtSenha"], input[name*="pass"], input[type="password"]', USER_PASS)
            page.click('input[type="submit"], button[type="submit"], input[id*="btnLogin"]')
            page.wait_for_load_state("networkidle")

        if page.url != URL_PAINEL:
            page.goto(URL_PAINEL)
            page.wait_for_load_state("networkidle")

        # 2. Preencher os DOIS campos de data com a data atual
        inputs_data = page.locator('input[type="text"]:visible, input[name*="Data"]:visible, input[id*="Data"]:visible').all()
        
        if len(inputs_data) >= 2:
            print(f"Preenchendo 1º campo de data com: {hoje}")
            inputs_data[0].fill(hoje)
            
            print(f"Preenchendo 2º campo de data com: {hoje}")
            inputs_data[1].fill(hoje)

        # 3. Preencher os horários (00:00 até 23:59)
        try:
            page.fill('input[name*="HoraInicio"], input[id*="HoraInicio"]', hora_inicio)
            page.fill('input[name*="HoraFim"], input[id*="HoraFim"]', hora_fim)
            print("Horários preenchidos (00:00 até 23:59).")
        except:
            campos_hora = page.locator('input[name*="Hora"]:visible, input[id*="Hora"]:visible').all()
            if len(campos_hora) >= 2:
                campos_hora[0].fill(hora_inicio)
                campos_hora[1].fill(hora_fim)

        # 4. Clicar em Pesquisar
        btn_pesquisar = page.locator('input[value*="Pesquisar"], button:has-text("Pesquisar"), input[id*="btnPesquisar"]')
        if btn_pesquisar.is_visible():
            print("Clicando no botão Pesquisar...")
            btn_pesquisar.click()
            page.wait_for_load_state("networkidle")

        # 5. Baixar arquivo exportado ou raspar a tabela HTML
        btn_exportar = page.locator('input[value*="Exportar"], a:has-text("Exportar"), input[value*="CSV"]')
        if btn_exportar.is_visible():
            print("Efetuando download do relatório...")
            with page.expect_download() as download_info:
                btn_exportar.click()
            download = download_info.value
            file_path = download.path()
            df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
        else:
            print("Botão de exportação direto não encontrado. Raspando a tabela da página...")
            table_html = page.locator("table.grid, table[id*='Grid'], table").first.outer_html()
            df = pd.read_html(table_html)[0]

        browser.close()
        return df

def substituir_dados_planilha(df):
    print(f"Conectando ao Google Sheets na aba '{NOME_ABA}'...")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    service_account_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    
    # Seleciona especificamente a aba "ATUAL"
    try:
        worksheet = spreadsheet.worksheet(NOME_ABA)
    except gspread.exceptions.WorksheetNotFound:
        # Se a aba não existir, cria automaticamente
        worksheet = spreadsheet.add_worksheet(title=NOME_ABA, rows=100, cols=20)

    # Tratar valores vazios para evitar erros
    df = df.fillna("")

    # Limpa apenas a aba "ATUAL" e insere os novos dados atualizados
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    print(f"Aba '{NOME_ABA}' atualizada com sucesso com os novos dados!")

if __name__ == "__main__":
    dados = extrair_relatorio_orvyx()
    substituir_dados_planilha(dados)
