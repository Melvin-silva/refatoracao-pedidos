# Relatório – Refatoração de `GerenciadorPedidos`

## 1. Code smells identificados

| # | Code smell | Onde aparece |
|---|-----------|--------------|
| 1 | **Long Method** | `processar_pedido` (~100 linhas: valida, calcula, baixa estoque, grava, envia e-mail, registra) |
| 2 | **Long Parameter List** | `processar_pedido` com 10 parâmetros |
| 3 | **Data Clumps** | `rua, numero, cidade, uf, cep` sempre juntos; `nome, email, tipo_cliente` também |
| 4 | **Primitive Obsession** | itens como `[str, str, str]` (com `int()`/`float()` espalhados); histórico como string `"nome\|tipo\|total"` que depois é `split`; tipo de cliente e pagamento como strings soltas |
| 5 | **Duplicated Code** | cálculo de desconto e frete copiado em `processar_pedido` e `calcular_orcamento` |
| 6 | **Magic Numbers / Magic Strings** | `0.05`, `500`, `300`, `12.5`, `22.9`, `"VIP"`, `"PIX"`, `10000`, `5`… |
| 7 | **Switch Statements (if/elif em cadeia)** | tipo de cliente (4 lugares) e forma de pagamento |
| 8 | **Divergent Change / Large Class (SRP)** | a classe muda por regra de preço, de frete, de estoque, de persistência, de e-mail e de relatório |
| 9 | **Hidden Dependencies / I/O embutido** | `open("pedidos.csv")` e `print` de e-mail dentro da regra de negócio; estoque fixo no construtor |
| 10 | **Command–Query Separation violada** | `verificar_estoque` consulta **e** dispara e-mail |
| 11 | **Retorno por string de erro** | `"ERRO: ..."` / `"OK: ..."` em vez de exceção/tipo |
| 12 | **Inconsistência (bug latente) causada pela duplicação** | `calcular_orcamento` não inclui `MA` no frete nordeste e não rejeita tipo desconhecido; `processar_pedido` inclui `MA` |

## 2. Testes de caracterização (`test_caracterizacao.py`)

61 casos que registram o comportamento atual, incluindo as esquisitices:

- todas as mensagens de erro e a **ordem** das validações;
- cálculo do total (descontos por tipo, limites exatos de 300 e 500, frete por UF, PIX, boleto, cartão com/sem juros, arredondamento);
- efeitos colaterais: baixa de estoque, limpeza do carrinho, linha do CSV, texto do e-mail, falha de escrita do CSV;
- `calcular_orcamento` (inclusive: não altera estado; tipo desconhecido sem erro; **MA = 39,90**);
- relatório, meta mensal, alerta de estoque, mensagem promocional;
- *quirk* registrado: linhas repetidas do mesmo produto burlam a checagem de estoque (estoque fica negativo).

Rodam com `pytest`. Eles usam diretório temporário, então não sujam o `pedidos.csv`.
Validei contra o original (61 verdes) e contra a versão refatorada (61 verdes).

## 3. Passos da refatoração (cada um termina em verde)

| Passo | Refatoração | Smell tratado | Princípio SOLID |
|------|-------------|---------------|-----------------|
| 1 | **Extract Constant** para números e textos mágicos | 6 | (legibilidade; base para OCP) |
| 2 | **Introduce Parameter Object**: `Endereco` e `Cliente` (com `validar()` e `formatado()`) | 2, 3 | **SRP** (cada objeto cuida da própria validação) |
| 3 | **Replace Primitive with Object**: `ItemPedido` (dataclass com `subtotal`) e `RegistroVenda` no lugar de listas/strings | 4 | **SRP**, **LSP/ISP** indiretos (contratos explícitos) |
| 4 | **Extract Class** `Estoque` (`validar`, `baixar`, `abaixo_do_minimo`) | 8 | **SRP** |
| 5 | **Extract Function** `calcular_frete` e `_subtotal_e_desconto`, usados também por `calcular_orcamento` | 5 | **DRY / SRP** |
| 6 | **Replace Conditional with Polymorphism**: `PoliticaComum/Vip/Funcionario` + Null Object `PoliticaDesconhecida`; dicionário `POLITICAS` | 7 | **OCP** (novo tipo = nova classe) e **LSP** (todas substituem `PoliticaCliente`) |
| 7 | **Replace Conditional with Polymorphism**: `Pix`, `Boleto`, `Cartao` + `criar_pagamento` | 7 | **OCP**, **SRP** |
| 8 | **Replace Error Code with Exception**: `ErroPedido`, convertida em `"ERRO: ..."` só na borda de `processar_pedido` | 11 | **SRP** (fluxo feliz separado do tratamento de erro) |
| 9 | **Extract Method** dividindo `processar_pedido` em `_fechar_pedido`, `_calcular_total`, `_notificar_cliente` | 1 | **SRP** |
| 10 | **Extract Class** `RepositorioPedidosCsv` e `NotificadorConsole`, **injetados** no construtor | 9 | **DIP** (regra de negócio depende de abstrações/colaboradores injetáveis) e **SRP** |
| 11 | **Separate Query from Modifier**: `produtos_com_estoque_baixo()` (pura) + `verificar_estoque()` | 10 | **SRP** / **ISP** (consultas sem efeitos) |
| 12 | **Correção deliberada (não é refatoração)**: após unificar o frete (passo 5), o orçamento passou a tratar `MA` como `processar_pedido` (22,90). O teste `test_orcamento_uf_MA` foi atualizado de 89,90 para 72,90 | 12 | — |

> Observação do passo 12: mudar comportamento é a única coisa que a regra
> "só refatore com testes verdes" não cobre. Por isso ficou como passo separado,
> com o teste alterado de propósito e comentado.

## 4. O que ficou como está (de propósito)

- A assinatura pública `processar_pedido` com 10 parâmetros foi mantida para não quebrar os testes de caracterização. Ela agora é uma fachada fina que cria `Cliente` e `Endereco`. Próximo passo possível: trocar a assinatura por `processar_pedido(cliente, endereco, pagamento)` e atualizar os testes.
- `adicionar_item` agora converte quantidade/preço na entrada (antes a conversão acontecia só ao processar). Só muda o momento em que valores inválidos geram `ValueError`.
- Bug do estoque com itens repetidos do mesmo produto continua (está registrado em teste). Corrigir seria uma mudança de comportamento.
