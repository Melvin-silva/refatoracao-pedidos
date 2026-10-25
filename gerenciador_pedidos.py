# PASSO 11 - Separate Query from Modifier: consulta pura de estoque baixo (SRP/ISP).
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

UFS_NORDESTE = {"PB", "AL", "RN", "BA", "SE", "CE", "PI", "MA"}
# QUIRK LEGADO: o orcamento original nao incluia MA. Mantido ate o passo 12.
UFS_NORDESTE_ORCAMENTO = UFS_NORDESTE - {"MA"}


class ErroPedido(Exception):
    """Violacao de regra de negocio ao processar um pedido."""


@dataclass
class Cliente:
    nome: str
    email: str
    tipo: str

    def validar(self):
        if self.nome is None or self.nome.strip() == "":
            raise ErroPedido("cliente sem nome")
        if self.email is None or "@" not in self.email or "." not in self.email:
            raise ErroPedido("email invalido")


@dataclass
class Endereco:
    rua: str
    numero: str
    cidade: str
    uf: str
    cep: str

    def validar(self):
        if self.cep is None or len(self.cep.replace("-", "")) != 8:
            raise ErroPedido("cep invalido")

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
        for item in itens:
            if item.produto not in self._quantidades:
                raise ErroPedido("produto inexistente " + item.produto)
            if self._quantidades[item.produto] < item.quantidade:
                raise ErroPedido("estoque insuficiente " + item.produto)

    def baixar(self, itens):
        for item in itens:
            self._quantidades[item.produto] -= item.quantidade

    def abaixo_do_minimo(self):
        return [(p, q) for p, q in self._quantidades.items() if q < ESTOQUE_MINIMO]


class PoliticaCliente:
    frete_gratis = False
    mensagem_promocional = ""
    mensagem_confirmacao = ""

    def desconto(self, subtotal):
        return 0


class PoliticaComum(PoliticaCliente):
    mensagem_promocional = "Compre acima de R$ 500 e ganhe 5% de desconto!"

    def desconto(self, subtotal):
        if subtotal > LIMITE_DESCONTO_PROMOCIONAL:
            return subtotal * DESCONTO_COMUM
        return 0


class PoliticaVip(PoliticaCliente):
    frete_gratis = True
    mensagem_promocional = "Ofertas exclusivas: 15% em compras acima de R$ 500!"
    mensagem_confirmacao = "Obrigado por ser VIP! Frete gratis garantido. "

    def desconto(self, subtotal):
        if subtotal > LIMITE_DESCONTO_PROMOCIONAL:
            return subtotal * DESCONTO_VIP_ACIMA_DO_LIMITE
        return subtotal * DESCONTO_VIP


class PoliticaFuncionario(PoliticaCliente):
    mensagem_promocional = "Lembrete: seu desconto de 20% vale em toda a loja."
    mensagem_confirmacao = "Desconto de colaborador aplicado. "

    def desconto(self, subtotal):
        return subtotal * DESCONTO_FUNCIONARIO


class PoliticaDesconhecida(PoliticaCliente):
    """Null Object: tipo nao cadastrado (sem desconto e sem mensagens)."""


POLITICAS = {
    "COMUM": PoliticaComum(),
    "VIP": PoliticaVip(),
    "FUNCIONARIO": PoliticaFuncionario(),
}
POLITICA_DESCONHECIDA = PoliticaDesconhecida()


def politica_para(tipo_cliente):
    return POLITICAS.get(tipo_cliente, POLITICA_DESCONHECIDA)


def calcular_frete(uf, valor_com_desconto, politica, ufs_nordeste=UFS_NORDESTE):
    if valor_com_desconto > LIMITE_FRETE_GRATIS or politica.frete_gratis:
        return 0
    if uf == "PE":
        return FRETE_PE
    if uf in ufs_nordeste:
        return FRETE_NORDESTE
    return FRETE_DEMAIS_ESTADOS


class Pix:
    def aplicar(self, total):
        return total * (1 - DESCONTO_PIX)


class Boleto:
    def aplicar(self, total):
        return total + TAXA_BOLETO


class Cartao:
    def __init__(self, parcelas):
        if parcelas < 1 or parcelas > MAX_PARCELAS:
            raise ErroPedido("parcelas invalidas")
        self.parcelas = parcelas

    def aplicar(self, total):
        if self.parcelas > PARCELAS_SEM_JUROS:
            return total * (1 + JUROS_POR_PARCELA * self.parcelas)
        return total


def criar_pagamento(forma, parcelas):
    if forma == "PIX":
        return Pix()
    if forma == "BOLETO":
        return Boleto()
    if forma == "CARTAO":
        return Cartao(parcelas)
    raise ErroPedido("forma de pagamento invalida")


class RepositorioPedidosCsv:
    def __init__(self, caminho="pedidos.csv"):
        self.caminho = caminho

    def salvar(self, cliente, forma_pagamento, total, texto_endereco):
        linha = (cliente.nome + ";" + cliente.email + ";" + cliente.tipo + ";"
                 + forma_pagamento + ";" + str(total) + ";" + texto_endereco + "\n")
        try:
            with open(self.caminho, "a", encoding="utf-8") as arquivo:
                arquivo.write(linha)
        except OSError as e:
            print("Falha ao salvar pedido: " + str(e))


class NotificadorConsole:
    def enviar_email(self, destinatario, mensagem):
        print("[EMAIL para " + destinatario + "] " + mensagem)


class GerenciadorPedidos:

    def __init__(self, estoque=None, repositorio=None, notificador=None):
        self.itens = []
        self.estoque = estoque if estoque is not None else Estoque()
        self.historico = []
        self.total_vendido = 0
        self._repositorio = repositorio if repositorio is not None else RepositorioPedidosCsv()
        self._notificador = notificador if notificador is not None else NotificadorConsole()

    def adicionar_item(self, produto, qtd, preco):
        self.itens.append(ItemPedido(produto, int(str(qtd)), float(str(preco))))

    def _subtotal_e_desconto(self, politica):
        subtotal = 0
        for item in self.itens:
            subtotal += item.subtotal
        return subtotal, politica.desconto(subtotal)

    def processar_pedido(self, nome, email, tipo_cliente, pagamento, parcelas,
                         rua, numero, cidade, uf, cep):
        cliente = Cliente(nome, email, tipo_cliente)
        endereco = Endereco(rua, numero, cidade, uf, cep)
        try:
            total = self._fechar_pedido(cliente, pagamento, parcelas, endereco)
        except ErroPedido as erro:
            return "ERRO: " + str(erro)
        return "OK: " + "%.2f" % total

    def _fechar_pedido(self, cliente, forma_pagamento, parcelas, endereco):
        cliente.validar()
        if len(self.itens) == 0:
            raise ErroPedido("pedido vazio")
        endereco.validar()
        self.estoque.validar(self.itens)
        if cliente.tipo not in POLITICAS:
            raise ErroPedido("tipo de cliente desconhecido")
        politica = POLITICAS[cliente.tipo]

        total = self._calcular_total(politica, endereco.uf, forma_pagamento, parcelas)

        self.estoque.baixar(self.itens)
        texto_endereco = endereco.formatado()
        self._repositorio.salvar(cliente, forma_pagamento, total, texto_endereco)
        self._notificar_cliente(cliente, politica, total, texto_endereco)

        self.historico.append(RegistroVenda(cliente.nome, cliente.tipo, total))
        self.total_vendido += total
        self.itens.clear()
        return total

    def _calcular_total(self, politica, uf, forma_pagamento, parcelas):
        subtotal, desconto = self._subtotal_e_desconto(politica)
        frete = calcular_frete(uf, subtotal - desconto, politica)
        pagamento = criar_pagamento(forma_pagamento, parcelas)
        total = pagamento.aplicar(subtotal - desconto + frete)
        return round(total * 100.0) / 100.0

    def _notificar_cliente(self, cliente, politica, total, texto_endereco):
        mensagem = "Ola " + cliente.nome + ", seu pedido foi confirmado. "
        mensagem += politica.mensagem_confirmacao
        mensagem += "Total: R$ " + "%.2f" % total + ". Entrega em: " + texto_endereco
        self._notificador.enviar_email(cliente.email, mensagem)

    def calcular_orcamento(self, tipo_cliente, uf):
        politica = politica_para(tipo_cliente)
        subtotal, desconto = self._subtotal_e_desconto(politica)
        frete = calcular_frete(uf, subtotal - desconto, politica,
                               UFS_NORDESTE_ORCAMENTO)
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

    def produtos_com_estoque_baixo(self):
        """Consulta pura: sem efeitos colaterais."""
        return self.estoque.abaixo_do_minimo()

    def verificar_estoque(self):
        alerta = ""
        for produto, quantidade in self.produtos_com_estoque_baixo():
            alerta += ("ALERTA: " + produto + " com estoque baixo ("
                       + str(quantidade) + ")\n")
            self._notificador.enviar_email(EMAIL_COMPRAS, "Repor " + produto)
        return alerta

    def mensagem_promocional(self, tipo_cliente):
        return politica_para(tipo_cliente).mensagem_promocional
