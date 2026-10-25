# PASSO 1 - Extract Constant: numeros e textos magicos viram constantes nomeadas.
LIMITE_DESCONTO_PROMOCIONAL = 500
LIMITE_FRETE_GRATIS = 300
META_MENSAL = 10000
ESTOQUE_MINIMO = 5
EMAIL_COMPRAS = "compras@loja.com"

FRETE_PE = 12.5
FRETE_NORDESTE = 22.9
FRETE_DEMAIS_ESTADOS = 39.9

DESCONTO_COMUM = 0.05
DESCONTO_VIP_ACIMA_DO_LIMITE = 0.15
DESCONTO_VIP = 0.10
DESCONTO_FUNCIONARIO = 0.20

DESCONTO_PIX = 0.05
TAXA_BOLETO = 2.5
MAX_PARCELAS = 12
PARCELAS_SEM_JUROS = 3
JUROS_POR_PARCELA = 0.0199


class GerenciadorPedidos:

    def __init__(self):
        self.itens = []
        self.estoque = {}
        self.historico = []
        self.total_vendido = 0
        self.estoque["CANETA"] = 100
        self.estoque["CADERNO"] = 50
        self.estoque["MOCHILA"] = 10
        self.estoque["CALCULADORA"] = 5

    def adicionar_item(self, produto, qtd, preco):
        self.itens.append([produto, str(qtd), str(preco)])

    def processar_pedido(self, nome, email, tipo_cliente, pagamento, parcelas,
                         rua, numero, cidade, uf, cep):
        if nome is None or nome.strip() == "":
            return "ERRO: cliente sem nome"
        if email is None or "@" not in email or "." not in email:
            return "ERRO: email invalido"
        if len(self.itens) == 0:
            return "ERRO: pedido vazio"
        if cep is None or len(cep.replace("-", "")) != 8:
            return "ERRO: cep invalido"
        for item in self.itens:
            if item[0] not in self.estoque:
                return "ERRO: produto inexistente " + item[0]
            if self.estoque[item[0]] < int(item[1]):
                return "ERRO: estoque insuficiente " + item[0]

        subtotal = 0
        for item in self.itens:
            subtotal += int(item[1]) * float(item[2])

        desconto = 0
        if tipo_cliente == "COMUM":
            if subtotal > LIMITE_DESCONTO_PROMOCIONAL:
                desconto = subtotal * DESCONTO_COMUM
        elif tipo_cliente == "VIP":
            if subtotal > LIMITE_DESCONTO_PROMOCIONAL:
                desconto = subtotal * DESCONTO_VIP_ACIMA_DO_LIMITE
            else:
                desconto = subtotal * DESCONTO_VIP
        elif tipo_cliente == "FUNCIONARIO":
            desconto = subtotal * DESCONTO_FUNCIONARIO
        else:
            return "ERRO: tipo de cliente desconhecido"

        frete = 0
        if uf == "PE":
            frete = FRETE_PE
        elif (uf == "PB" or uf == "AL" or uf == "RN" or uf == "BA"
              or uf == "SE" or uf == "CE" or uf == "PI" or uf == "MA"):
            frete = FRETE_NORDESTE
        else:
            frete = FRETE_DEMAIS_ESTADOS
        if subtotal - desconto > LIMITE_FRETE_GRATIS or tipo_cliente == "VIP":
            frete = 0

        total = subtotal - desconto + frete
        if pagamento == "PIX":
            total = total * (1 - DESCONTO_PIX)
        elif pagamento == "BOLETO":
            total = total + TAXA_BOLETO
        elif pagamento == "CARTAO":
            if parcelas < 1 or parcelas > MAX_PARCELAS:
                return "ERRO: parcelas invalidas"
            if parcelas > PARCELAS_SEM_JUROS:
                total = total * (1 + JUROS_POR_PARCELA * parcelas)
        else:
            return "ERRO: forma de pagamento invalida"
        total = round(total * 100.0) / 100.0

        for item in self.itens:
            self.estoque[item[0]] = self.estoque[item[0]] - int(item[1])

        endereco = rua + ", " + numero + ", " + cidade + "/" + uf + ", CEP " + cep

        try:
            f = open("pedidos.csv", "a", encoding="utf-8")
            f.write(nome + ";" + email + ";" + tipo_cliente + ";" + pagamento + ";"
                    + str(total) + ";" + endereco + "\n")
            f.close()
        except OSError as e:
            print("Falha ao salvar pedido: " + str(e))

        mensagem = "Ola " + nome + ", seu pedido foi confirmado. "
        if tipo_cliente == "VIP":
            mensagem += "Obrigado por ser VIP! Frete gratis garantido. "
        elif tipo_cliente == "FUNCIONARIO":
            mensagem += "Desconto de colaborador aplicado. "
        mensagem += "Total: R$ " + "%.2f" % total + ". Entrega em: " + endereco
        print("[EMAIL para " + email + "] " + mensagem)

        self.historico.append(nome + "|" + tipo_cliente + "|" + str(total))
        self.total_vendido += total
        self.itens.clear()
        return "OK: " + "%.2f" % total

    def calcular_orcamento(self, tipo_cliente, uf):
        subtotal = 0
        for item in self.itens:
            subtotal += int(item[1]) * float(item[2])
        desconto = 0
        if tipo_cliente == "COMUM":
            if subtotal > LIMITE_DESCONTO_PROMOCIONAL:
                desconto = subtotal * DESCONTO_COMUM
        elif tipo_cliente == "VIP":
            if subtotal > LIMITE_DESCONTO_PROMOCIONAL:
                desconto = subtotal * DESCONTO_VIP_ACIMA_DO_LIMITE
            else:
                desconto = subtotal * DESCONTO_VIP
        elif tipo_cliente == "FUNCIONARIO":
            desconto = subtotal * DESCONTO_FUNCIONARIO
        frete = 0
        if uf == "PE":
            frete = FRETE_PE
        elif (uf == "PB" or uf == "AL" or uf == "RN" or uf == "BA"
              or uf == "SE" or uf == "CE" or uf == "PI"):
            frete = FRETE_NORDESTE
        else:
            frete = FRETE_DEMAIS_ESTADOS
        if subtotal - desconto > LIMITE_FRETE_GRATIS or tipo_cliente == "VIP":
            frete = 0
        return round((subtotal - desconto + frete) * 100.0) / 100.0

    def gerar_relatorio(self):
        r = "=== RELATORIO DE VENDAS ===\n"
        vip = 0
        comum = 0
        func = 0
        for h in self.historico:
            partes = h.split("|")
            if partes[1] == "VIP":
                vip += 1
            elif partes[1] == "COMUM":
                comum += 1
            elif partes[1] == "FUNCIONARIO":
                func += 1
            r += partes[0] + " (" + partes[1] + "): R$ " + "%.2f" % float(partes[2]) + "\n"
        r += "Pedidos VIP: " + str(vip) + "\n"
        r += "Pedidos COMUM: " + str(comum) + "\n"
        r += "Pedidos FUNCIONARIO: " + str(func) + "\n"
        r += "Total vendido: R$ " + "%.2f" % self.total_vendido + "\n"
        if self.total_vendido > META_MENSAL:
            r += "Meta mensal atingida!\n"
        return r

    def verificar_estoque(self):
        alerta = ""
        for produto in self.estoque:
            if self.estoque[produto] < ESTOQUE_MINIMO:
                alerta += ("ALERTA: " + produto + " com estoque baixo ("
                           + str(self.estoque[produto]) + ")\n")
                print("[EMAIL para " + EMAIL_COMPRAS + "] Repor " + produto)
        return alerta

    def mensagem_promocional(self, tipo_cliente):
        if tipo_cliente == "VIP":
            return "Ofertas exclusivas: 15% em compras acima de R$ 500!"
        elif tipo_cliente == "COMUM":
            return "Compre acima de R$ 500 e ganhe 5% de desconto!"
        elif tipo_cliente == "FUNCIONARIO":
            return "Lembrete: seu desconto de 20% vale em toda a loja."
        else:
            return ""
