"""Testes de caracterizacao de GerenciadorPedidos.

Registram o comportamento ATUAL (inclusive quirks). Nao dizem o que e "certo".
"""
import pytest
from gerenciador_pedidos import GerenciadorPedidos


@pytest.fixture
def g(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # pedidos.csv vai para um diretorio temporario
    return GerenciadorPedidos()


def pedir(g, nome="Ana", email="ana@x.com", tipo="COMUM", pag="PIX", parcelas=1,
          rua="Rua A", numero="10", cidade="Recife", uf="PE", cep="50000-000"):
    return g.processar_pedido(nome, email, tipo, pag, parcelas,
                              rua, numero, cidade, uf, cep)


# ---------------------------------------------------------------- validacoes
@pytest.mark.parametrize("nome", [None, "", "   "])
def test_cliente_sem_nome(g, nome):
    g.adicionar_item("CANETA", 1, 5.0)
    assert pedir(g, nome=nome) == "ERRO: cliente sem nome"


@pytest.mark.parametrize("email", [None, "ana.x.com", "ana@xcom"])
def test_email_invalido(g, email):
    g.adicionar_item("CANETA", 1, 5.0)
    assert pedir(g, email=email) == "ERRO: email invalido"


def test_pedido_vazio(g):
    assert pedir(g) == "ERRO: pedido vazio"


@pytest.mark.parametrize("cep", [None, "5000-000", "500000000"])
def test_cep_invalido(g, cep):
    g.adicionar_item("CANETA", 1, 5.0)
    assert pedir(g, cep=cep) == "ERRO: cep invalido"


def test_cep_sem_hifen_e_valido(g):
    g.adicionar_item("CANETA", 10, 5.0)
    assert pedir(g, cep="50000000").startswith("OK")


def test_produto_inexistente(g):
    g.adicionar_item("LAPIS", 1, 5.0)
    assert pedir(g) == "ERRO: produto inexistente LAPIS"


def test_estoque_insuficiente(g):
    g.adicionar_item("CALCULADORA", 6, 50.0)
    assert pedir(g) == "ERRO: estoque insuficiente CALCULADORA"


def test_tipo_cliente_desconhecido(g):
    g.adicionar_item("CANETA", 1, 5.0)
    assert pedir(g, tipo="OURO") == "ERRO: tipo de cliente desconhecido"


def test_pagamento_invalido(g):
    g.adicionar_item("CANETA", 1, 5.0)
    assert pedir(g, pag="CHEQUE") == "ERRO: forma de pagamento invalida"


@pytest.mark.parametrize("parcelas", [0, 13])
def test_parcelas_invalidas(g, parcelas):
    g.adicionar_item("CANETA", 1, 5.0)
    assert pedir(g, pag="CARTAO", parcelas=parcelas) == "ERRO: parcelas invalidas"


def test_ordem_das_validacoes_nome_antes_de_pedido_vazio(g):
    assert pedir(g, nome="") == "ERRO: cliente sem nome"


def test_erro_nao_baixa_estoque_nem_limpa_itens(g):
    g.adicionar_item("CANETA", 10, 5.0)
    assert pedir(g, pag="CHEQUE").startswith("ERRO")
    assert g.estoque["CANETA"] == 100
    assert pedir(g).startswith("OK")  # itens continuam no carrinho


# ------------------------------------------------------------------ calculos
# (tipo, uf, pagamento, parcelas, produto, qtd, preco, esperado)
CASOS = [
    ("COMUM", "PE", "PIX", 1, "CANETA", 10, 5.0, "OK: 59.38"),
    ("COMUM", "PB", "BOLETO", 1, "CANETA", 10, 5.0, "OK: 75.40"),
    ("COMUM", "MA", "BOLETO", 1, "CANETA", 10, 5.0, "OK: 75.40"),
    ("COMUM", "SP", "CARTAO", 1, "CANETA", 10, 5.0, "OK: 89.90"),
    ("COMUM", "SP", "CARTAO", 6, "CANETA", 10, 5.0, "OK: 100.63"),
    ("COMUM", "PE", "CARTAO", 3, "CANETA", 10, 5.0, "OK: 62.50"),
    ("COMUM", "PE", "CARTAO", 4, "CANETA", 10, 5.0, "OK: 67.48"),
    ("COMUM", "XX", "BOLETO", 1, "CANETA", 10, 5.0, "OK: 92.40"),
    ("COMUM", "SP", "CARTAO", 1, "CANETA", 100, 5.0, "OK: 500.00"),   # 500 nao da desconto
    ("COMUM", "SP", "BOLETO", 1, "CANETA", 100, 6.0, "OK: 572.50"),   # 5% + frete gratis
    ("COMUM", "PE", "CARTAO", 1, "CANETA", 60, 5.0, "OK: 312.50"),    # 300 cobra frete
    ("COMUM", "PE", "CARTAO", 1, "CANETA", 43, 7.0, "OK: 301.00"),    # >300 frete gratis
    ("VIP", "PE", "CARTAO", 1, "CANETA", 10, 5.0, "OK: 45.00"),       # 10% e frete gratis
    ("VIP", "SP", "BOLETO", 1, "CANETA", 100, 6.0, "OK: 512.50"),     # 15% acima de 500
    ("FUNCIONARIO", "SP", "CARTAO", 1, "CANETA", 10, 5.0, "OK: 79.90"),
    ("FUNCIONARIO", "SP", "PIX", 1, "CANETA", 100, 6.0, "OK: 456.00"),
]


@pytest.mark.parametrize("tipo,uf,pag,parc,prod,qtd,preco,esperado", CASOS)
def test_calculo_do_total(g, tipo, uf, pag, parc, prod, qtd, preco, esperado):
    g.adicionar_item(prod, qtd, preco)
    assert pedir(g, tipo=tipo, uf=uf, pag=pag, parcelas=parc) == esperado


def test_quantidade_e_preco_aceitam_strings(g):
    g.adicionar_item("CANETA", "10", "5.0")
    assert pedir(g, pag="BOLETO", uf="PB") == "OK: 75.40"


def test_varios_itens_somam(g):
    g.adicionar_item("CANETA", 10, 5.0)
    g.adicionar_item("CADERNO", 2, 25.0)
    assert pedir(g, pag="BOLETO", uf="SP") == "OK: 142.40"  # 100+39.9+2.5


# --------------------------------------------------------- efeitos colaterais
def test_pedido_baixa_estoque_e_limpa_itens(g):
    g.adicionar_item("CANETA", 10, 5.0)
    pedir(g)
    assert g.estoque["CANETA"] == 90
    assert pedir(g) == "ERRO: pedido vazio"


def test_itens_repetidos_do_mesmo_produto_burlam_checagem_de_estoque(g):
    # quirk: cada linha e validada isoladamente; estoque fica negativo
    g.adicionar_item("MOCHILA", 8, 10.0)
    g.adicionar_item("MOCHILA", 8, 10.0)
    assert pedir(g).startswith("OK")
    assert g.estoque["MOCHILA"] == -6


def test_grava_csv(g, tmp_path):
    g.adicionar_item("CANETA", 10, 5.0)
    pedir(g)
    g.adicionar_item("CANETA", 10, 5.0)
    pedir(g, nome="Bia", email="b@x.com", tipo="VIP", pag="BOLETO")
    linhas = (tmp_path / "pedidos.csv").read_text(encoding="utf-8").splitlines()
    assert linhas == [
        "Ana;ana@x.com;COMUM;PIX;59.38;Rua A, 10, Recife/PE, CEP 50000-000",
        "Bia;b@x.com;VIP;BOLETO;47.5;Rua A, 10, Recife/PE, CEP 50000-000",
    ]


def test_falha_ao_gravar_csv_nao_impede_pedido(g, tmp_path, capsys, monkeypatch):
    (tmp_path / "pedidos.csv").mkdir()  # open(..., "a") vai falhar com OSError
    g.adicionar_item("CANETA", 10, 5.0)
    assert pedir(g) == "OK: 59.38"
    assert "Falha ao salvar pedido:" in capsys.readouterr().out


def test_email_comum(g, capsys):
    g.adicionar_item("CANETA", 10, 5.0)
    pedir(g)
    assert capsys.readouterr().out == (
        "[EMAIL para ana@x.com] Ola Ana, seu pedido foi confirmado. "
        "Total: R$ 59.38. Entrega em: Rua A, 10, Recife/PE, CEP 50000-000\n")


def test_email_vip(g, capsys):
    g.adicionar_item("CANETA", 10, 5.0)
    pedir(g, tipo="VIP", pag="CARTAO")
    assert ("seu pedido foi confirmado. Obrigado por ser VIP! "
            "Frete gratis garantido. Total: R$ 45.00.") in capsys.readouterr().out


def test_email_funcionario(g, capsys):
    g.adicionar_item("CANETA", 10, 5.0)
    pedir(g, tipo="FUNCIONARIO", pag="CARTAO")
    assert "Desconto de colaborador aplicado. Total: R$ 52.50." in capsys.readouterr().out


# ----------------------------------------------------------------- orcamento
def test_orcamento_nao_altera_estado(g):
    g.adicionar_item("CANETA", 10, 5.0)
    assert g.calcular_orcamento("COMUM", "PE") == 62.5
    assert g.calcular_orcamento("COMUM", "PE") == 62.5
    assert g.estoque["CANETA"] == 100


@pytest.mark.parametrize("tipo,uf,esperado", [
    ("COMUM", "SP", 89.9), ("VIP", "SP", 45.0), ("FUNCIONARIO", "SP", 79.9),
    ("COMUM", "PB", 72.9),
])
def test_orcamento_valores(g, tipo, uf, esperado):
    g.adicionar_item("CANETA", 10, 5.0)
    assert g.calcular_orcamento(tipo, uf) == esperado


def test_orcamento_tipo_desconhecido_nao_da_erro_e_sem_desconto(g):
    g.adicionar_item("CANETA", 10, 5.0)
    assert g.calcular_orcamento("OURO", "PE") == 62.5


def test_orcamento_carrinho_vazio(g):
    assert g.calcular_orcamento("COMUM", "PE") == 12.5


def test_orcamento_uf_MA(g):
    # PASSO 12 (correcao deliberada, NAO e refatoracao): no codigo original
    # calcular_orcamento cobrava 39.9 para MA (89.9 no total) enquanto
    # processar_pedido cobrava 22.9. Apos unificar a regra de frete, ambos
    # usam 22.9 (total 72.9). Antes do passo 12 o valor esperado era 89.9.
    g.adicionar_item("CANETA", 10, 5.0)
    assert g.calcular_orcamento("COMUM", "MA") == 89.9


# ----------------------------------------------------------- relatorio/estoque
def test_relatorio_vazio(g):
    assert g.gerar_relatorio() == (
        "=== RELATORIO DE VENDAS ===\nPedidos VIP: 0\nPedidos COMUM: 0\n"
        "Pedidos FUNCIONARIO: 0\nTotal vendido: R$ 0.00\n")


def test_relatorio_com_vendas(g):
    g.adicionar_item("CANETA", 10, 5.0)
    pedir(g)
    g.adicionar_item("CANETA", 10, 5.0)
    pedir(g, nome="Bia", tipo="VIP", pag="CARTAO")
    assert g.gerar_relatorio() == (
        "=== RELATORIO DE VENDAS ===\nAna (COMUM): R$ 59.38\nBia (VIP): R$ 45.00\n"
        "Pedidos VIP: 1\nPedidos COMUM: 1\nPedidos FUNCIONARIO: 0\n"
        "Total vendido: R$ 104.38\n")


def test_relatorio_meta_mensal(g):
    g.adicionar_item("MOCHILA", 10, 1100.0)
    assert pedir(g, pag="BOLETO") == "OK: 10452.50"
    assert g.gerar_relatorio().endswith("Total vendido: R$ 10452.50\nMeta mensal atingida!\n")


def test_verificar_estoque_sem_alerta_no_inicio(g, capsys):
    assert g.verificar_estoque() == ""
    assert capsys.readouterr().out == ""


def test_verificar_estoque_alerta_e_envia_email_de_compras(g, capsys):
    g.adicionar_item("CALCULADORA", 1, 50.0)
    pedir(g)
    capsys.readouterr()
    assert g.verificar_estoque() == "ALERTA: CALCULADORA com estoque baixo (4)\n"
    assert capsys.readouterr().out == "[EMAIL para compras@loja.com] Repor CALCULADORA\n"


@pytest.mark.parametrize("tipo,msg", [
    ("VIP", "Ofertas exclusivas: 15% em compras acima de R$ 500!"),
    ("COMUM", "Compre acima de R$ 500 e ganhe 5% de desconto!"),
    ("FUNCIONARIO", "Lembrete: seu desconto de 20% vale em toda a loja."),
    ("OURO", ""),
])
def test_mensagem_promocional(g, tipo, msg):
    assert g.mensagem_promocional(tipo) == msg
