# PASSO 4 - Extract Class: Estoque (SRP).
from dataclasses import dataclass

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


@dataclass
class Cliente:
    nome: str
    email: str
    tipo: str

    def validar(self):
        """Retorna mensagem de erro ou None."""
        if self.nome is None or self.nome.strip() == "":
            return "ERRO: cliente sem nome"
        if self.email is None or "@" not in self.email or "." not in self.email:
            return "ERRO: email invalido"
        return None


@dataclass
class Endereco:
    rua: str
    numero: str
    cidade: str
    uf: str
    cep: str

    def validar(self):
        if self.cep is None or len(self.cep.replace("-", "")) != 8:
            return "ERRO: cep invalido"
        return None

    def formatado(self):
        return (self.rua + ", " + self.numero + ", " + self.cidade + "/"
                + self.uf + ", CEP " + self.cep)


@dataclass
class ItemPedido:
    produto: str
    quantidade: int
    preco: float

    @property
    def subtotal(self):
        return self.quantidade * self.preco


@dataclass
class RegistroVenda:
    nome: str
    tipo_cliente: str
    total: float


class Estoque:
    def __init__(self):
        self._quantidades = {
            "CANETA": 100,
            "CADERNO": 50,
            "MOCHILA": 10,
            "CALCULADORA": 5,
        }

    def __getitem__(self, produto):
        return self._quantidades[produto]

    def validar(self, itens):
        """Retorna mensagem de erro ou None."""
        for item in itens:
            if item.produto not in self._quantidades:
                return "ERRO: produto inexistente " + item.produto
            if self._quantidades[item.produto] < item.quantidade:
                return "ERRO: estoque insuficiente " + item.produto
        return None

    def baixar(self, itens):
        for item in itens:
            self._quantidades[item.produto] -= item.quantidade

    def abaixo_do_minimo(self):
        return [(p, q) for p, q in self._quantidades.items() if q < ESTOQUE_MINIMO]


class GerenciadorPedidos:

    def __init__(self):
        self.itens = []
        self.estoque = Estoque()
        self.historico = []
        self.total_vendido = 0

    def adicionar_item(self, produto, qtd, preco):
        self.itens.append(ItemPedido(produto, int(str(qtd)), float(str(preco))))

    def processar_pedido(self, nome, email, tipo_cliente, pagamento, parcelas,
                         rua, numero, cidade, uf, cep):
        cliente = Cliente(nome, email, tipo_cliente)
        endereco = Endereco(rua, numero, cidade, uf, cep)

        erro = cliente.validar()
        if erro:
            return erro
        if len(self.itens) == 0:
            return "ERRO: pedido vazio"
        erro = endereco.validar()
        if erro:
            return erro
        erro = self.estoque.validar(self.itens)
        if erro:
            return erro

        subtotal = 0
        for item in self.itens:
            subtotal += item.subtotal

        desconto = 0
        if cliente.tipo == "COMUM":
            if subtotal > LIMITE_DESCONTO_PROMOCIONAL:
                desconto = subtotal * DESCONTO_COMUM
        elif cliente.tipo == "VIP":
            if subtotal > LIMITE_DESCONTO_PROMOCIONAL:
                desconto = subtotal * DESCONTO_VIP_ACIMA_DO_LIMITE
            else:
                desconto = subtotal * DESCONTO_VIP
        elif cliente.tipo == "FUNCIONARIO":
            desconto = subtotal * DESCONTO_FUNCIONARIO
        else:
            return "ERRO: tipo de cliente desconhecido"

        frete = 0
        if endereco.uf == "PE":
            frete = FRETE_PE
        elif (endereco.uf == "PB" or endereco.uf == "AL" or endereco.uf == "RN"
              or endereco.uf == "BA" or endereco.uf == "SE" or endereco.uf == "CE"
              or endereco.uf == "PI" or endereco.uf == "MA"):
            frete = FRETE_NORDESTE
        else:
            frete = FRETE_DEMAIS_ESTADOS
        if subtotal - desconto > LIMITE_FRETE_GRATIS or cliente.tipo == "VIP":
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

        self.estoque.baixar(self.itens)

        texto_endereco = endereco.formatado()

        try:
            f = open("pedidos.csv", "a", encoding="utf-8")
            f.write(cliente.nome + ";" + cliente.email + ";" + cliente.tipo + ";"
                    + pagamento + ";" + str(total) + ";" + texto_endereco + "\n")
            f.close()
        except OSError as e:
            print("Falha ao salvar pedido: " + str(e))

        mensagem = "Ola " + cliente.nome + ", seu pedido foi confirmado. "
        if cliente.tipo == "VIP":
            mensagem += "Obrigado por ser VIP! Frete gratis garantido. "
        elif cliente.tipo == "FUNCIONARIO":
            mensagem += "Desconto de colaborador aplicado. "
        mensagem += "Total: R$ " + "%.2f" % total + ". Entrega em: " + texto_endereco
        print("[EMAIL para " + cliente.email + "] " + mensagem)

        self.historico.append(RegistroVenda(cliente.nome, cliente.tipo, total))
        self.total_vendido += total
        self.itens.clear()
        return "OK: " + "%.2f" % total

    def calcular_orcamento(self, tipo_cliente, uf):
        subtotal = 0
        for item in self.itens:
            subtotal += item.subtotal
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
        for venda in self.historico:
            if venda.tipo_cliente == "VIP":
                vip += 1
            elif venda.tipo_cliente == "COMUM":
                comum += 1
            elif venda.tipo_cliente == "FUNCIONARIO":
                func += 1
            r += (venda.nome + " (" + venda.tipo_cliente + "): R$ "
                  + "%.2f" % venda.total + "\n")
        r += "Pedidos VIP: " + str(vip) + "\n"
        r += "Pedidos COMUM: " + str(comum) + "\n"
        r += "Pedidos FUNCIONARIO: " + str(func) + "\n"
        r += "Total vendido: R$ " + "%.2f" % self.total_vendido + "\n"
        if self.total_vendido > META_MENSAL:
            r += "Meta mensal atingida!\n"
        return r

    def verificar_estoque(self):
        alerta = ""
        for produto, quantidade in self.estoque.abaixo_do_minimo():
            alerta += ("ALERTA: " + produto + " com estoque baixo ("
                       + str(quantidade) + ")\n")
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
