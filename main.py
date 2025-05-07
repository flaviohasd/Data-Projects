import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

st.set_page_config(page_title="Analisador de Ações", layout="wide")
st.title("📊 Analisador de Ações - Brasil e EUA")

# Funções de formatação
def formatar_valor(valor, tipo="padrao", moeda="R$"):
    try:
        if valor is None:
            return "N/A"
        if tipo == "porcentagem":
            return f"{valor:.2f}%"
        elif tipo == "moeda":
            return f"{moeda} {valor:,.2f}"
        else:
            return f"{valor:.2f}"
    except:
        return "N/A"

def formatar_grandes_numeros(valor):
    try:
        valor = float(valor)
        for unidade in ['', 'K', 'M', 'B', 'T']:
            if abs(valor) < 1000:
                return f"{valor:.2f}{unidade}"
            valor /= 1000
        return f"{valor:.2f}T"
    except:
        return valor

# Carregar bases de tickers com caminhos relativos
@st.cache_data
def carregar_tickers():
    try:
        base_path = os.path.join(os.path.dirname(__file__), "database")
        b3 = pd.read_csv(os.path.join(base_path, "tickers_b3.csv"))
        nyse = pd.read_csv(os.path.join(base_path, "tickers_nyse.csv"))
        nasdaq = pd.read_csv(os.path.join(base_path, "tickers_nasdaq.csv"))
        return pd.concat([b3, nyse, nasdaq], ignore_index=True)
    except Exception as e:
        st.error(f"Erro ao carregar os arquivos de tickers: {e}")
        return pd.DataFrame(columns=["Nome", "Ticker"])

tickers_df = carregar_tickers()

st.subheader("🔍 Buscar empresas por nome")
empresa_input = st.multiselect("Digite o nome da empresa:", options=tickers_df["Nome"].tolist())

st.write("📅 Selecione o período do histórico de preços:")
periodo = st.selectbox(
    "Período",
    options=[
        ("1d", "1 Dia"),
        ("5d", "5 Dias"),
        ("1mo", "1 Mês"),
        ("3mo", "3 Meses"),
        ("6mo", "6 Meses"),
        ("ytd", "Ano Atual (YTD)"),
        ("1y", "1 Ano"),
        ("5y", "5 Anos"),
        ("10y", "10 Anos"),
        ("max", "Desde o Início")
    ],
    index=6,
    format_func=lambda x: x[1]
)

st.write("📈 Configurações de Médias Móveis:")
ma_periodos = st.multiselect("Selecione os períodos das médias móveis:", [20, 50, 100, 200], default=[20, 50])

if empresa_input:
    tickers_selecionados = tickers_df[tickers_df["Nome"].isin(empresa_input)]["Ticker"].tolist()
    dados_acoes = {}

    for ticker in tickers_selecionados:
        try:
            acao = yf.Ticker(ticker)
            info = acao.info
            hist = acao.history(period=periodo[0])
            moeda = "R$" if ".SA" in ticker else "$"

            for ma in ma_periodos:
                hist[f"MA_{ma}"] = hist["Close"].rolling(window=ma).mean()

            dados_acoes[ticker] = {
                "info": info,
                "hist": hist,
                "moeda": moeda,
                "financials": acao.financials,
                "balance_sheet": acao.balance_sheet,
                "cashflow": acao.cashflow
            }
        except Exception as e:
            st.error(f"Erro ao processar o ticker {ticker}: {e}")

    st.subheader("📊 Comparativo de Indicadores")
    indicadores = ["regularMarketPrice", "trailingPE", "priceToBook", "dividendYield", "returnOnEquity"]
    dados_indicadores = []

    for ticker, dados in dados_acoes.items():
        info = dados["info"]
        moeda = dados["moeda"]
        dy = info.get("dividendYield") or 0
        linha = {
            "Ticker": ticker,
            "Preço Atual": formatar_valor(info.get("regularMarketPrice"), "moeda", moeda),
            "P/L": formatar_valor(info.get("trailingPE")),
            "P/VP": formatar_valor(info.get("priceToBook")),
            "Dividend Yield": formatar_valor(dy, "porcentagem"),
            "ROE": formatar_valor((info.get("returnOnEquity") or 0) * 100, "porcentagem")
        }
        dados_indicadores.append(linha)

    df_indicadores = pd.DataFrame(dados_indicadores)
    st.dataframe(df_indicadores, use_container_width=True)

    st.subheader("📈 Gráficos Avançados")
    for ticker, dados in dados_acoes.items():
        st.write(f"**{ticker}**")
        hist = dados["hist"]

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"],
            name="Candlestick"
        ))

        for ma in ma_periodos:
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist[f"MA_{ma}"],
                mode='lines',
                name=f"MA {ma}"
            ))

        fig.update_layout(
            xaxis_title='Data',
            yaxis_title='Preço',
            xaxis_rangeslider_visible=True,
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📄 Demonstrativos Financeiros")
    for ticker, dados in dados_acoes.items():
        st.markdown(f"### {ticker}")

        st.markdown("**Demonstração de Resultados (DRE):**")
        st.dataframe(dados["financials"].applymap(formatar_grandes_numeros))

        st.markdown("**Balanço Patrimonial:**")
        st.dataframe(dados["balance_sheet"].applymap(formatar_grandes_numeros))

        st.markdown("**Fluxo de Caixa:**")
        st.dataframe(dados["cashflow"].applymap(formatar_grandes_numeros))