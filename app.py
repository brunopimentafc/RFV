# Imports
import pandas as pd
import streamlit as st
import numpy as np

from datetime import datetime
from PIL import Image
from io import BytesIO


# --- Funções utilitárias ---

@st.cache_data
def convert_df(df):
    """Converte o dataframe em CSV para download."""
    return df.to_csv(index=False).encode('utf-8')


@st.cache_data
def to_excel(df):
    """Converte o dataframe em Excel para download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data


# --- Funções de classificação RFV ---

def recencia_class(x, r, q_dict):
    """Classifica recência — menor é melhor."""
    if x <= q_dict[r][0.25]:
        return 'A'
    elif x <= q_dict[r][0.50]:
        return 'B'
    elif x <= q_dict[r][0.75]:
        return 'C'
    else:
        return 'D'


def freq_val_class(x, fv, q_dict):
    """Classifica frequência/valor — maior é melhor."""
    if x <= q_dict[fv][0.25]:
        return 'D'
    elif x <= q_dict[fv][0.50]:
        return 'C'
    elif x <= q_dict[fv][0.75]:
        return 'B'
    else:
        return 'A'


# --- Função principal da aplicação ---

def main():
    st.set_page_config(
        page_title='RFV',
        layout="wide",
        initial_sidebar_state='expanded'
    )

    st.write("""
    # RFV

    RFV significa **Recência, Frequência e Valor**, e é utilizado para segmentar clientes com base em seu comportamento de compras.
    Essa segmentação permite realizar **ações de marketing e CRM mais direcionadas**, auxiliando na personalização e retenção de clientes.

    Para cada cliente, calculamos:

    - **Recência (R):** Dias desde a última compra  
    - **Frequência (F):** Número total de compras  
    - **Valor (V):** Total gasto no período  

    Vamos calcular tudo isso abaixo 👇
    """)
    st.markdown("---")

    # --- Escolha da fonte de dados ---
    st.sidebar.write("## Fonte de dados")
    usar_padrao = st.sidebar.checkbox("Usar arquivo de exemplo (dados_input.csv)", value=True)

    if usar_padrao:
        st.sidebar.info("Usando o arquivo de exemplo embutido.")
        try:
            df_compras = pd.read_csv("dados_input.csv", parse_dates=['DiaCompra'], infer_datetime_format=True)
        except FileNotFoundError:
            st.error("Arquivo 'dados_input.csv' não encontrado. Coloque-o na mesma pasta do app.py.")
            st.stop()
    else:
        data_file_1 = st.sidebar.file_uploader("Envie seu arquivo CSV/XLSX", type=['csv', 'xlsx'])
        if data_file_1 is not None:
            if data_file_1.name.endswith('.csv'):
                df_compras = pd.read_csv(data_file_1, parse_dates=['DiaCompra'], infer_datetime_format=True)
            else:
                df_compras = pd.read_excel(data_file_1, parse_dates=['DiaCompra'])
        else:
            st.warning("Envie um arquivo ou marque a opção de exemplo para visualizar os dados.")
            st.stop()

    # --- Recência ---
    st.write('## Recência (R)')
    dia_atual = df_compras['DiaCompra'].max()
    st.write(f"Dia máximo na base de dados: **{dia_atual.date()}**")

    df_recencia = df_compras.groupby(by='ID_cliente', as_index=False)['DiaCompra'].max()
    df_recencia.columns = ['ID_cliente', 'DiaUltimaCompra']
    df_recencia['Recencia'] = df_recencia['DiaUltimaCompra'].apply(lambda x: (dia_atual - x).days)
    df_recencia.drop('DiaUltimaCompra', axis=1, inplace=True)
    st.write(df_recencia.head())

    # --- Frequência ---
    st.write('## Frequência (F)')
    df_frequencia = df_compras[['ID_cliente', 'CodigoCompra']].groupby('ID_cliente').count().reset_index()
    df_frequencia.columns = ['ID_cliente', 'Frequencia']
    st.write(df_frequencia.head())

    # --- Valor ---
    st.write('## Valor (V)')
    df_valor = df_compras[['ID_cliente', 'ValorTotal']].groupby('ID_cliente').sum().reset_index()
    df_valor.columns = ['ID_cliente', 'Valor']
    st.write(df_valor.head())

    # --- Tabela RFV ---
    st.write('## Tabela RFV final')
    df_RFV = (
        df_recencia
        .merge(df_frequencia, on='ID_cliente')
        .merge(df_valor, on='ID_cliente')
        .set_index('ID_cliente')
    )
    st.write(df_RFV.head())

    # --- Segmentação ---
    st.write('## Segmentação utilizando o RFV')
    quartis = df_RFV.quantile(q=[0.25, 0.5, 0.75])
    st.write(quartis)

    df_RFV['R_quartil'] = df_RFV['Recencia'].apply(recencia_class, args=('Recencia', quartis))
    df_RFV['F_quartil'] = df_RFV['Frequencia'].apply(freq_val_class, args=('Frequencia', quartis))
    df_RFV['V_quartil'] = df_RFV['Valor'].apply(freq_val_class, args=('Valor', quartis))
    df_RFV['RFV_Score'] = df_RFV['R_quartil'] + df_RFV['F_quartil'] + df_RFV['V_quartil']
    st.write(df_RFV.head())

    # --- Contagem de clientes por grupo ---
    st.write('### Quantidade de clientes por grupos')
    st.write(df_RFV['RFV_Score'].value_counts())

    # --- Clientes AAA ---
    st.write('#### Top 10 clientes (AAA)')
    st.write(df_RFV[df_RFV['RFV_Score'] == 'AAA'].sort_values('Valor', ascending=False).head(10))

    # --- Ações de marketing ---
    st.write('## Ações de marketing/CRM')
    dict_acoes = {
        'AAA': 'Enviar cupons de desconto, pedir indicação, enviar amostras grátis de novos produtos.',
        'DDD': 'Clientes inativos com baixo gasto — monitorar ou desconsiderar ações.',
        'DAA': 'Clientes que gastaram bastante mas estão sumindo — enviar cupom de reativação.',
        'CAA': 'Clientes que gastaram bastante mas estão sumindo — enviar cupom de reativação.'
    }

    df_RFV['acoes de marketing/crm'] = df_RFV['RFV_Score'].map(dict_acoes)
    st.write(df_RFV.head())

    # --- Download ---
    df_xlsx = to_excel(df_RFV)
    st.download_button(
        label='📥 Baixar tabela RFV (Excel)',
        data=df_xlsx,
        file_name='RFV_clientes.xlsx'
    )

    # --- Resumo final ---
    st.write('### Quantidade de clientes por tipo de ação')
    st.write(df_RFV['acoes de marketing/crm'].value_counts(dropna=False))


if __name__ == '__main__':
    main()
