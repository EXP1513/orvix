import os
import json
from datetime import datetime

import gspread
from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials

# =====================================================
# CONFIGURAÇÕES
# =====================================================

PLANILHA_ID = "1Vi4c-w36lLMkJA4LzQkVRPbcHdSxT1DsxO-OtKOrIsU"
NOME_ABA = "ATUAL"

URL_LOGIN = "https://atendimento.redeservice.com.br/administrador/login.aspx"
URL_PESQUISA = "https://atendimento.redeservice.com.br/administrador/sala_pesquisar.aspx"

USER_LOGIN = os.environ.get("USER_LOGIN")
USER_SENHA = os.environ.get("USER_SENHA")

# =====================================================
# GOOGLE SHEETS
# =====================================================

def atualizar_google_sheets(dados):

    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not creds_json:
        raise ValueError(
            "Secret GOOGLE_SERVICE_ACCOUNT_JSON não encontrado."
        )

    creds_dict = json.loads(creds_json)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes
    )

    client = gspread.authorize(credentials)

    planilha = client.open_by_key(PLANILHA_ID)

    worksheet = planilha.worksheet(NOME_ABA)

    worksheet.clear()

    if dados:
        worksheet.update("A1", dados)
        print(f"{len(dados)} linhas enviadas para o Google Sheets.")
    else:
        print("Nenhum dado encontrado.")

# =====================================================
# ORVIX
# =====================================================

def extrair_relatorio_orvyx():

    hoje = datetime.now().strftime("%d/%m/%Y")

    print(f"Iniciando extração - {hoje}")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        # LOGIN
        print("Abrindo login...")
        page.goto(URL_LOGIN, wait_until="networkidle")

        page.wait_for_selector('input[type="text"]')
        page.wait_for_selector('input[type="password"]')

        page.locator(
            'input[type="text"]'
        ).first.fill(USER_LOGIN)

        page.locator(
            'input[type="password"]'
        ).first.fill(USER_SENHA)

        page.locator(
            'input[type="submit"], button[type="submit"], input[value*="Entrar"]'
        ).first.click()

        page.wait_for_load_state("networkidle")

        # RELATÓRIO
        print("Abrindo página de pesquisa...")
        page.goto(
            URL_PESQUISA,
            wait_until="networkidle"
        )

        page.wait_for_timeout(3000)

        # DATA INICIAL / FINAL
        campos_texto = page.locator(
            'input[type="text"]'
        ).all()

        if len(campos_texto) >= 2:
            campos_texto[0].fill(hoje)
            campos_texto[1].fill(hoje)

        # HORÁRIO
        campos_hora = page.locator(
            'input[name*="hora"], input[id*="hora"]'
        ).all()

        if len(campos_hora) >= 2:
            campos_hora[0].fill("00:00")
            campos_hora[1].fill("23:59")

        print("Executando pesquisa...")

        page.locator(
            'input[type="submit"], button:has-text("Pesquisar"), button:has-text("Buscar")'
        ).first.click()

        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(5000)

        print("Extraindo tabela...")

        dados = []

        linhas = page.locator("table tr").all()

        for linha in linhas:

            colunas = linha.locator(
                "td, th"
            ).all_text_contents()

            colunas = [
                c.strip()
                for c in colunas
            ]

            if any(colunas):
                dados.append(colunas)

        browser.close()

        print(
            f"{len(dados)} linhas encontradas."
        )

        return dados

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    if not USER_LOGIN:
        raise ValueError(
            "Secret USER_LOGIN não encontrado."
        )

    if not USER_SENHA:
        raise ValueError(
            "Secret USER_SENHA não encontrado."
        )

    dados = extrair_relatorio_orvyx()

    atualizar_google_sheets(dados)

    print("Processo concluído.")
