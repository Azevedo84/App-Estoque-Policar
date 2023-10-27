import toga
from toga.style import Pack
from toga.style.pack import CENTER, COLUMN, ROW, LEFT, RIGHT, Pack
from toga.constants import COLUMN, CENTER
from toga import ScrollContainer
from toga.style import Pack
from toga.handlers import wrapped_handler
from functools import partial
import io
import os
import textwrap

import http.client
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from urllib.parse import urlencode, quote
import re
import locale


class BancoAnder:
    def __init__(self):
        self.dados = {}

    def inserir(self, tabela, dados):
        if tabela not in self.dados:
            self.dados[tabela] = []
        self.dados[tabela].append(dados)

    def consultar(self, tabela):
        return self.dados.get(tabela, [])

    def consultar_cond(self, tabela, campo, condicao):
        return [dado for dado in self.dados.get(tabela, []) if dado.get(campo) == condicao]

    def consultar_entre_datas(self, tabela, campo, data_inicio, data_fim):
        data_inicio = datetime.strptime(data_inicio, '%d/%m/%Y')
        data_fim = datetime.strptime(data_fim, '%d/%m/%Y')

        return [dado for dado in self.dados.get(tabela, []) if
                data_inicio <= datetime.strptime(dado.get(campo), '%d/%m/%Y') <= data_fim]

    def atualizar(self, tabela, indice, dados):
        if tabela in self.dados and 0 <= indice < len(self.dados[tabela]):
            self.dados[tabela][indice] = dados

    def deletar(self, tabela, indice):
        if tabela in self.dados and 0 <= indice < len(self.dados[tabela]):
            del self.dados[tabela][indice]

    def atualizar_por_campo(self, tabela, campo, valor, campos_atualizacao):
        if tabela in self.dados:
            for indice, registro in enumerate(self.dados[tabela]):
                if campo in registro and registro[campo] == valor:
                    for campo_atualizacao, valor_atualizacao in campos_atualizacao.items():
                        self.dados[tabela][indice][campo_atualizacao] = valor_atualizacao

    def deletar_por_campo(self, tabela, campo, valor):
        if tabela in self.dados:
            indices_para_remover = []
            for indice, registro in enumerate(self.dados[tabela]):
                if campo in registro and registro[campo] == valor:
                    indices_para_remover.append(indice)

            for indice in reversed(indices_para_remover):
                self.deletar(tabela, indice)


class ConexaoBack4App:
    def __init__(self, banco):
        self.connection = http.client.HTTPSConnection('parseapi.back4app.com', 443)
        self.cabecalhos = {
            "X-Parse-Application-Id": "2lPiQxvRL7UooDimPCQCW7kek3HsdiRB2DBpbAJf",
            "X-Parse-REST-API-Key": "j0aPeKTI0eD9ZPWmGRun8gJmEb265Wmh0NVjmbsu",
            "Content-Type": "application/json"
        }

        self.bc_ander = banco

    def query_sem_argumentos(self, tabela, campo_ordem):
        parametro = {'order': campo_ordem}
        query_string = urlencode(parametro)
        url = f'/classes/{tabela}?{query_string}'
        self.connection.request('GET', url, headers=self.cabecalhos)
        resposta = self.connection.getresponse()
        resultado = json.loads(resposta.read())
        lista_resultado = resultado['results']

        return lista_resultado

    def query_1_argumento(self, tabela, coluna, linhas, campo_ordem):
        parametro = {'where': json.dumps({coluna: linhas}), 'order': campo_ordem}
        query_string = urlencode(parametro)
        url = f'/classes/{tabela}?{query_string}'
        self.connection.request('GET', url, headers=self.cabecalhos)
        resposta = self.connection.getresponse()
        resultado = json.loads(resposta.read())
        lista_resultado = resultado['results']

        return lista_resultado

    def query_2_argumentos(self, tabela, coluna1, linha1, coluna2, linha2, campo_ordem):
        lista_resultado = []
        parametro = {'where': json.dumps({coluna1: linha1, coluna2: linha2}), 'order': campo_ordem}
        query_string = urlencode(parametro)
        url = f'/classes/{tabela}?{query_string}'
        self.connection.request('GET', url, headers=self.cabecalhos)
        resposta = self.connection.getresponse()
        resultado = json.loads(resposta.read())
        if resultado:
            lista_resultado = resultado['results']

        return lista_resultado

    def query_3_argumentos(self, tabela, coluna1, linha1, coluna2, linha2, coluna3, linha3, campo_ordem):
        parametro = {'where': json.dumps({coluna1: linha1, coluna2: linha2, coluna3: linha3}), 'order': campo_ordem}
        query_string = urlencode(parametro)
        url = f'/classes/{tabela}?{query_string}'
        self.connection.request('GET', url, headers=self.cabecalhos)
        resposta = self.connection.getresponse()
        resultado = json.loads(resposta.read())

        if 'error' in resultado:
            lista_resultado = []
        else:
            lista_resultado = resultado['results']

        return lista_resultado

    def obter_usuario(self, username, senha):
        dados_usuario = []

        url = "/login?username={}&password={}".format(username, senha)
        self.connection.request('GET', url, headers=self.cabecalhos)
        response = self.connection.getresponse()
        response_data = response.read().decode('utf-8')
        result = json.loads(response_data)

        if 'objectId' in result:
            user_id = result['objectId']
        else:
            user_id = None

        if 'username' in result:
            user_nome = result['username']
        else:
            user_nome = None

        if 'email' in result:
            user_email = result['email']
        else:
            user_email = None

        dados = (user_id, user_nome, user_email)
        dados_usuario.append(dados)

        self.bc_ander.inserir('tab_user', {'objectId': user_id, 'username': user_nome, 'email': user_email})

        return result, dados_usuario

    def obter_produtos(self):
        resultado = self.query_sem_argumentos('produto', 'DESCRICAO')

        for dados in resultado:
            id_prod = dados['objectId']
            nome_prod = dados['DESCRICAO']
            um_prod = dados['UM']
            estoque_prod = dados['ESTOQUE']

            if dados and 'OBS' in dados:
                obs_prod = dados['OBS']
            else:
                obs_prod = ''

            if dados and 'IMAGEM' in dados:
                imagem_prod = dados['IMAGEM']
            else:
                imagem_prod = ''

            id_grupo = dados['ID_GRUPO']['objectId']

            self.bc_ander.inserir('tab_produto', {'objectId': id_prod,
                                                  'DESCRICAO': nome_prod,
                                                  'UM': um_prod,
                                                  'ESTOQUE': estoque_prod,
                                                  'OBS': obs_prod,
                                                  'IMAGEM': imagem_prod,
                                                  'ID_GRUPO': id_grupo})

    def obter_grupos(self):
        resultado = self.query_sem_argumentos('grupo_produto', 'DESCRICAO')

        for dados in resultado:
            id_gr = dados['objectId']
            nome_gr = dados['DESCRICAO']

            self.bc_ander.inserir('tab_grupo_produto', {'objectId': id_gr,
                                                        'DESCRICAO': nome_gr})

    def obter_funcionarios(self):
        resultado = self.query_sem_argumentos('funcionario', 'NOME')

        for dados in resultado:
            id_func = dados['objectId']
            nome_func = dados['NOME']

            self.bc_ander.inserir('tab_funcionario', {'objectId': id_func,
                                                  'NOME': nome_func})

    def obter_entradas(self):
        resultado = self.query_sem_argumentos('entrada','DATA_ENTRADA' )

        for dados in resultado:
            id_entrad = dados['objectId']
            data_entrada = dados['DATA_ENTRADA']
            id_produto = dados['ID_PRODUTO']['objectId']
            qtde = dados['QTDE_ENTRADA']

            if dados and 'OBS' in dados:
                obs_prod = dados['OBS']
            else:
                obs_prod = ''

            self.bc_ander.inserir('tab_entrada', {'objectId': id_entrad,
                                                  'DATA_ENTRADA': data_entrada,
                                                  'ID_PRODUTO': id_produto,
                                                  'QTDE_ENTRADA': qtde,
                                                  'OBS': obs_prod})

    def obter_saidas(self):
        resultado = self.query_sem_argumentos('saida', 'DATA_SAIDA')

        for dados in resultado:
            id_saida = dados['objectId']
            data_saida = dados['DATA_SAIDA']
            id_produto = dados['ID_PRODUTO']['objectId']
            id_func = dados['ID_FUNCIONARIO']['objectId']
            qtde = dados['QTDE_SAIDA']
            obs = dados['OBS']

            self.bc_ander.inserir('tab_saida', {'objectId': id_saida,
                                                  'DATA_SAIDA': data_saida,
                                                  'ID_PRODUTO': id_produto,
                                                    'ID_FUNCIONARIO': id_func,
                                                  'QTDE_SAIDA': qtde,
                                                'OBS': obs})

    def salvar_no_banco(self, objetos):
        dados_json = json.dumps({"requests": objetos})

        url = '/batch'

        self.connection.request('POST', url, headers=self.cabecalhos, body=dados_json)

        response = self.connection.getresponse()
        response_data = response.read().decode('utf-8')

        result = json.loads(response_data)

        self.connection.close()

        return result


class EstoquePolicar(toga.App):

    def startup(self):
        self.bc_ander = BancoAnder()
        self.conexao = ConexaoBack4App(self.bc_ander)

        self.conexao.obter_produtos()
        self.conexao.obter_grupos()
        self.conexao.obter_funcionarios()
        self.conexao.obter_entradas()
        self.conexao.obter_saidas()

        box_principal = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.main_window = toga.MainWindow()
        self.main_window.content = box_principal
        self.main_window.show()
        self.mostrar_tela_principal(self.main_window)


    def mostrar_tela_principal(self, widget):
        banco = self.bc_ander

        self.tela_principal = TelaPrincipal(widget, banco)
        self.tela_principal.startup()


class TelaPrincipal:
    def __init__(self, main_window, banco):
        self.bc_ander = banco
        self.conexao = ConexaoBack4App(self.bc_ander)

        self.scroll_container = toga.ScrollContainer(style=Pack(flex=1))

        box_principal = toga.Box(style=Pack(direction=COLUMN, padding=10))

        titulo = self.cria_titulo_pri()
        box_principal.add(titulo)

        btn_entrada = toga.Button(f'Entradas', style=Pack(padding=10),
                                  on_press=partial(self.mostrar_tela_entrada))
        box_principal.add(btn_entrada)

        btn_saida = toga.Button(f'Saídas', style=Pack(padding=10),
                                on_press=partial(self.mostrar_tela_saida))
        box_principal.add(btn_saida)

        btn_relatorio = toga.Button(f'Relatório - Estoque', style=Pack(padding=10),
                                    on_press=partial(self.mostrar_tela_estoque))
        box_principal.add(btn_relatorio)

        btn_relatorio = toga.Button(f'Relatório - Movimentação', style=Pack(padding=10),
                                    on_press=partial(self.mostrar_tela_movimentacao))
        box_principal.add(btn_relatorio)

        btn_produtos = toga.Button(f'Cadastro - Produtos', style=Pack(padding=10),
                                   on_press=partial(self.mostrar_tela_produto))
        box_principal.add(btn_produtos)

        btn_grupo = toga.Button(f'Cadastro - Grupo de Produtos', style=Pack(padding=10),
                                on_press=partial(self.mostrar_tela_grupo_produto))
        box_principal.add(btn_grupo)

        btn_func = toga.Button(f'Cadastro - Funcionários', style=Pack(padding=10),
                               on_press=partial(self.mostrar_tela_funcionario))
        box_principal.add(btn_func)

        self.scroll_container.content = box_principal

        self.main_window = main_window

    def cria_titulo_pri(self):
        self.box_dois = toga.Box(style=Pack(direction=COLUMN, alignment="center", padding=5))
        self.name_box = toga.Box(style=Pack(direction=ROW))

        self.button = toga.Label('Tela Principal', style=Pack(font_size=25, font_weight='bold'))

        self.width = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))
        self.height = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))

        self.btn_box = toga.Box(style=Pack(direction=ROW))
        self.btn_box.add(self.button)

        self.box_dois.add(self.name_box)
        self.box_dois.add(self.width, self.btn_box, self.height)

        return self.box_dois

    def startup(self):
        self.main_window.content = self.scroll_container

    def mostrar_tela_produto(self, widget):
        banco = self.bc_ander

        self.tela_produto = Produtos(self.main_window, banco)
        self.tela_produto.startup()

    def mostrar_tela_grupo_produto(self, widget):
        banco = self.bc_ander

        self.tela_grupo = GrupodeProdutos(self.main_window, banco)
        self.tela_grupo.startup()

    def mostrar_tela_funcionario(self, widget):
        banco = self.bc_ander

        self.tela_funcionario = Funcionarios(self.main_window, banco)
        self.tela_funcionario.startup()

    def mostrar_tela_entrada(self, widget):
        banco = self.bc_ander

        self.tela_entrada = Entradas(self.main_window, banco)
        self.tela_entrada.startup()

    def mostrar_tela_saida(self, widget):
        banco = self.bc_ander

        self.tela_saida = Saidas(self.main_window, banco)
        self.tela_saida.startup()

    def mostrar_tela_estoque(self, widget):
        banco = self.bc_ander

        tela_estoque = Estoque(self.main_window, banco)
        tela_estoque.startup()

    def mostrar_tela_movimentacao(self, widget):
        banco = self.bc_ander

        tela_mov = Movimentacao(self.main_window, banco)
        tela_mov.startup()


class Produtos:
    def __init__(self, main_window, banco):
        self.bc_ander = banco
        self.conexao = ConexaoBack4App(self.bc_ander)

        self.scroll_container = toga.ScrollContainer(style=Pack(flex=1))
        self.box_final = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))
        box1 = self.cria_box1()
        self.box_final.add(box1)
        self.scroll_container.content = self.box_final

        self.main_window = main_window

    def cria_espaco_branco(self):
        box = toga.Box(style=Pack(direction=ROW))
        button = toga.Label(' ', style=Pack(font_size=10, font_weight='bold'))
        box.add(button)

        return box

    def cria_titulo(self):
        self.box_dois = toga.Box(style=Pack(direction=COLUMN, alignment="center", padding=5))
        self.name_box = toga.Box(style=Pack(direction=ROW))

        self.button = toga.Label('Cadastro de Produtos', style=Pack(font_size=25, font_weight='bold'))

        self.width = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))
        self.height = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))

        self.btn_box = toga.Box(style=Pack(direction=ROW))
        self.btn_box.add(self.button)

        self.box_dois.add(self.name_box)
        self.box_dois.add(self.width, self.btn_box, self.height)

        return self.box_dois

    def cria_text_descricao_prod(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Produto:', style=Pack(flex=1 / 4, padding_top=13))
        box_login.add(button)

        self.text_nome_prod = toga.TextInput(placeholder="Nome do Produto", style=Pack(flex=1))
        box_login.add(self.text_nome_prod)

        return box_login

    def cria_combo_um(self):
        self.lista_box_check = []

        box = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Unidade Medida:', style=Pack(flex=1/3, padding=3))
        box.add(button)

        opcoes = []
        opcoes_selection = []

        dados0_op = ("gEa25nMGNW", "UN")
        dados1_op = ("ODPShER1Z7", "LT")
        dados2_op = ("IQRX4CG1pn", "KG")
        dados3_op = ("ECegwZaHAY", "MT")

        opcoes.append(dados0_op)
        opcoes.append(dados1_op)
        opcoes.append(dados2_op)
        opcoes.append(dados3_op)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_um = toga.Selection(items=opcoes_selection, style=Pack(flex=1, padding=3))
        box.add(self.selection_um)

        return box

    def cria_combo_grupos(self):
        self.lista_box_check = []

        box = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Grupo:', style=Pack(flex=1/3, padding=3))
        box.add(button)

        opcoes = []
        opcoes_selection = []

        dados_banco = self.bc_ander.consultar('tab_grupo_produto')

        for itens in dados_banco:
            id_gr = itens['objectId']
            nome_gr = itens['DESCRICAO']

            dados = (id_gr, nome_gr)
            opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_gr = toga.Selection(items=opcoes_selection, style=Pack(flex=1, padding=3))
        box.add(self.selection_gr)

        self.lista_box_check.append(self.selection_gr)  # Adiciona o self.box_check à lista

        return box

    def cria_text_obs_prod(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Obs:', style=Pack(flex=1 / 4, padding_top=13))
        box_login.add(button)

        self.text_obs_prod = toga.TextInput(placeholder="Observação", style=Pack(flex=1))
        box_login.add(self.text_obs_prod)

        return box_login

    def cria_btn_salvar(self):
        self.box_btn_finalizar = toga.Box(style=Pack(direction=COLUMN, padding=10))
        self.btn_finalizar = toga.Button('Salvar',
                                         on_press=self.salvar_produto,
                                         style=Pack(padding_bottom=5))
        self.box_btn_finalizar.add(self.btn_finalizar)

        return self.box_btn_finalizar

    def cria_btn_voltar_princ(self):
        self.box_btn_principal = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.btn_tela_principal = toga.Button('Ir para Tela Principal',
                                              on_press=self.mostrar_tela_principal,
                                              style=Pack(padding_bottom=5))
        self.box_btn_principal.add(self.btn_tela_principal)

        return self.box_btn_principal

    def cria_box1(self):
        self.box_semifinal1 = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))

        branco = self.cria_espaco_branco()
        branco1 = self.cria_espaco_branco()
        branco2 = self.cria_espaco_branco()
        branco3 = self.cria_espaco_branco()
        branco4 = self.cria_espaco_branco()
        branco5 = self.cria_espaco_branco()

        titulo = self.cria_titulo()
        descricao = self.cria_text_descricao_prod()
        combo_um = self.cria_combo_um()
        combo_gr = self.cria_combo_grupos()
        obs = self.cria_text_obs_prod()
        salvar = self.cria_btn_salvar()
        btn_principal = self.cria_btn_voltar_princ()

        self.box_semifinal1.add(branco, titulo,
                                branco1, descricao,
                                branco2, combo_um,
                                branco3, combo_gr,
                                branco4, obs,
                                branco5, salvar, btn_principal)

        return self.box_semifinal1

    def startup(self):
        self.main_window.content = self.scroll_container

    def mostrar_tela_principal(self, widget):
        banco = self.bc_ander

        self.tela_principal = TelaPrincipal(self.main_window, banco)
        self.tela_principal.startup()

    def salvar_produto(self, widget):
        lista_json = []
        dados_post = []

        if self.text_nome_prod.value:
            texto_editado = self.text_nome_prod.value
            texto_editado = texto_editado.upper()

            nome_gr_escolhido = self.selection_gr.value
            id_gr_escolhido = ''

            dados_banco = self.bc_ander.consultar('tab_grupo_produto')
            for itens in dados_banco:
                nome_gr = itens['DESCRICAO']

                if nome_gr_escolhido == nome_gr:
                    id_gr = itens['objectId']
                    id_gr_escolhido = id_gr

            um_escolhido = self.selection_um.value

            if self.text_obs_prod.value:
                obs_editado = self.text_obs_prod.value
                obs_editado = obs_editado.upper()
            else:
                obs_editado = ''

            print("POST")
            objeto = {"method": "POST", "path": "/classes/produto",
                      "body": {"ID_GRUPO": {"__type": "Pointer",
                                            "className": "grupo_produto",
                                            "objectId": id_gr_escolhido},
                               "DESCRICAO": texto_editado,
                               "UM": um_escolhido,
                               "ESTOQUE": "0.00",
                               "OBS": obs_editado}}
            lista_json.append(objeto)

            dadinhos = (texto_editado, um_escolhido, "0.00", obs_editado, '', id_gr_escolhido)
            dados_post.append(dadinhos)

            final = 0

            if lista_json:
                final = final + 1
                result = self.conexao.salvar_no_banco(lista_json)
                if dados_post:
                    id_prod_result = result[0]['success']['objectId']
                    nome_prod, um_prod, estoque_prod, obs_prod, imagem_prod, id_grupo = dados_post[0]

                    self.bc_ander.inserir('tab_produto', {'objectId': id_prod_result,
                                                          'DESCRICAO': nome_prod,
                                                          'UM': um_prod,
                                                          'ESTOQUE': estoque_prod,
                                                          'OBS': obs_prod,
                                                          'IMAGEM': imagem_prod,
                                                          'ID_GRUPO': id_grupo})

            if final > 0:
                self.mostrar_tela_principal(widget)
                self.main_window.info_dialog("Atenção!", f'DADOS SALVO COM SUCESSO!')
            else:
                self.main_window.info_dialog("Atenção!", f'ALGUM ITEM PRECISA SER\n ALTERADO PARA SALVAR!')
        else:
            self.main_window.info_dialog("Atenção!", 'O campo "Produto" não pode estar vazio!')


class GrupodeProdutos:
    def __init__(self, main_window, banco):
        self.bc_ander = banco
        self.conexao = ConexaoBack4App(self.bc_ander)

        self.scroll_container = toga.ScrollContainer(style=Pack(flex=1))
        self.box_final = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))
        box1 = self.cria_box1()
        self.box_final.add(box1)
        self.scroll_container.content = self.box_final

        self.main_window = main_window

    def cria_espaco_branco(self):
        box = toga.Box(style=Pack(direction=ROW))
        button = toga.Label(' ', style=Pack(font_size=10, font_weight='bold'))
        box.add(button)

        return box

    def cria_titulo(self):
        self.box_dois = toga.Box(style=Pack(direction=COLUMN, alignment="center", padding=5))
        self.name_box = toga.Box(style=Pack(direction=ROW))

        self.button = toga.Label('Cadastro de Grupo de Produtos', style=Pack(font_size=25, font_weight='bold'))

        self.width = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))
        self.height = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))

        self.btn_box = toga.Box(style=Pack(direction=ROW))
        self.btn_box.add(self.button)

        self.box_dois.add(self.name_box)
        self.box_dois.add(self.width, self.btn_box, self.height)

        return self.box_dois

    def cria_text_descricao_grupo(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Grupo:', style=Pack(flex=1 / 4, padding_top=13))
        box_login.add(button)

        self.textinput_grupo = toga.TextInput(placeholder="Nome do Grupo de Produto", style=Pack(flex=1))
        box_login.add(self.textinput_grupo)

        return box_login

    def cria_btn_salvar(self):
        box_btn_finalizar = toga.Box(style=Pack(direction=COLUMN, padding=10))
        btn_finalizar = toga.Button('Salvar',
                                         on_press=self.salvar_grupo,
                                         style=Pack(padding_bottom=5))
        box_btn_finalizar.add(btn_finalizar)

        return box_btn_finalizar

    def cria_btn_voltar_princ(self):
        self.box_btn_principal = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.btn_tela_principal = toga.Button('Ir para Tela Principal',
                                              on_press=self.mostrar_tela_principal,
                                              style=Pack(padding_bottom=5))
        self.box_btn_principal.add(self.btn_tela_principal)

        return self.box_btn_principal

    def cria_box1(self):
        self.box_semifinal1 = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))

        branco = self.cria_espaco_branco()
        branco1 = self.cria_espaco_branco()
        branco2 = self.cria_espaco_branco()

        titulo = self.cria_titulo()
        descricao = self.cria_text_descricao_grupo()
        salvar = self.cria_btn_salvar()
        btn_principal = self.cria_btn_voltar_princ()

        self.box_semifinal1.add(branco, titulo, branco1, descricao, branco2, salvar, btn_principal)

        return self.box_semifinal1

    def startup(self):
        self.main_window.content = self.scroll_container

    def mostrar_tela_principal(self, widget):
        banco = self.bc_ander

        self.tela_principal = TelaPrincipal(self.main_window, banco)
        self.tela_principal.startup()

    def salvar_grupo(self, widget):
        lista_json = []
        dados_post = []

        if self.textinput_grupo.value:
            texto_editado = self.textinput_grupo.value
            texto_editado = texto_editado.upper()

            print("POST")
            objeto = {"method": "POST", "path": "/classes/grupo_produto",
                      "body": {"DESCRICAO": texto_editado}}
            lista_json.append(objeto)

            dados_post.append(texto_editado)

            final = 0

            if lista_json:
                final = final + 1
                result = self.conexao.salvar_no_banco(lista_json)
                if dados_post:
                    id_gr_result = result[0]['success']['objectId']
                    nome_gr = dados_post[0]

                    self.bc_ander.inserir('tab_grupo_produto', {'objectId': id_gr_result,
                                                          'DESCRICAO': nome_gr})

            if final > 0:
                self.mostrar_tela_principal(widget)
                self.main_window.info_dialog("Atenção!", f'DADOS SALVO COM SUCESSO!')
            else:
                self.main_window.info_dialog("Atenção!", f'ALGUM ITEM PRECISA SER\n ALTERADO PARA SALVAR!')
        else:
            self.main_window.info_dialog("Atenção!", 'O campo "Grupo" não pode estar vazio!')


class Funcionarios:
    def __init__(self, main_window, banco):
        self.bc_ander = banco
        self.conexao = ConexaoBack4App(self.bc_ander)

        self.scroll_container = toga.ScrollContainer(style=Pack(flex=1))
        self.box_final = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))
        box1 = self.cria_box1()
        self.box_final.add(box1)
        self.scroll_container.content = self.box_final

        self.main_window = main_window

    def cria_espaco_branco(self):
        box = toga.Box(style=Pack(direction=ROW))
        button = toga.Label(' ', style=Pack(font_size=10, font_weight='bold'))
        box.add(button)

        return box

    def cria_titulo(self):
        self.box_dois = toga.Box(style=Pack(direction=COLUMN, alignment="center", padding=5))
        self.name_box = toga.Box(style=Pack(direction=ROW))

        self.button = toga.Label('Cadastro de Funcionários', style=Pack(font_size=25, font_weight='bold'))

        self.width = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))
        self.height = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))

        self.btn_box = toga.Box(style=Pack(direction=ROW))
        self.btn_box.add(self.button)

        self.box_dois.add(self.name_box)
        self.box_dois.add(self.width, self.btn_box, self.height)

        return self.box_dois

    def cria_text_descricao_func(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Nome:', style=Pack(flex=1/4, padding_top=13))
        box_login.add(button)

        self.textinput_func = toga.TextInput(placeholder="Nome do Funcionário", style=Pack(flex=1))
        box_login.add(self.textinput_func)

        return box_login

    def cria_btn_salvar(self):
        self.box_btn_finalizar = toga.Box(style=Pack(direction=COLUMN, padding=10))
        self.btn_finalizar = toga.Button('Salvar',
                                         on_press=self.salvar_funcionario,
                                         style=Pack(padding_bottom=5))
        self.box_btn_finalizar.add(self.btn_finalizar)

        return self.box_btn_finalizar

    def cria_btn_voltar_princ(self):
        self.box_btn_principal = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.btn_tela_principal = toga.Button('Ir para Tela Principal',
                                              on_press=self.mostrar_tela_principal,
                                              style=Pack(padding_bottom=5))
        self.box_btn_principal.add(self.btn_tela_principal)

        return self.box_btn_principal

    def cria_box1(self):
        self.box_semifinal1 = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))

        branco = self.cria_espaco_branco()
        branco1 = self.cria_espaco_branco()
        branco2 = self.cria_espaco_branco()

        titulo = self.cria_titulo()
        descricao = self.cria_text_descricao_func()
        salvar = self.cria_btn_salvar()
        btn_principal = self.cria_btn_voltar_princ()

        self.box_semifinal1.add(branco, titulo, branco1, descricao, branco2, salvar, btn_principal)

        return self.box_semifinal1

    def startup(self):
        self.main_window.content = self.scroll_container

    def mostrar_tela_principal(self, widget):
        banco = self.bc_ander

        self.tela_principal = TelaPrincipal(self.main_window, banco)
        self.tela_principal.startup()

    def salvar_funcionario(self, widget):
        lista_json = []
        dados_post = []

        if self.textinput_func.value:
            texto_editado = self.textinput_func.value
            texto_editado = texto_editado.upper()

            print("POST")
            objeto = {"method": "POST", "path": "/classes/funcionario",
                      "body": {"NOME": texto_editado}}
            lista_json.append(objeto)

            dados_post.append(texto_editado)

            final = 0

            if lista_json:
                final = final + 1
                result = self.conexao.salvar_no_banco(lista_json)
                if dados_post:
                    id_func_result = result[0]['success']['objectId']
                    nome_func = dados_post[0]

                    self.bc_ander.inserir('tab_funcionario', {'objectId': id_func_result,
                                                                'NOME': nome_func})

            if final > 0:
                self.mostrar_tela_principal(widget)
                self.main_window.info_dialog("Atenção!", f'DADOS SALVO COM SUCESSO!')
            else:
                self.main_window.info_dialog("Atenção!", f'ALGUM ITEM PRECISA SER\n ALTERADO PARA SALVAR!')
        else:
            self.main_window.info_dialog("Atenção!", 'O campo "Nome" não pode estar vazio!')


class Entradas:
    def __init__(self, main_window, banco):
        self.bc_ander = banco
        self.conexao = ConexaoBack4App(self.bc_ander)

        self.scroll_container = toga.ScrollContainer(style=Pack(flex=1))
        self.box_final = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))
        box1 = self.cria_box1()
        self.box_final.add(box1)
        self.scroll_container.content = self.box_final

        self.main_window = main_window

    def cria_espaco_branco(self):
        box = toga.Box(style=Pack(direction=ROW))
        button = toga.Label(' ', style=Pack(font_size=10, font_weight='bold'))
        box.add(button)

        return box

    def cria_titulo(self):
        self.box_dois = toga.Box(style=Pack(direction=COLUMN, alignment="center", padding=5))
        self.name_box = toga.Box(style=Pack(direction=ROW))

        self.button = toga.Label('Entrada de Produtos', style=Pack(font_size=25, font_weight='bold'))

        self.width = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))
        self.height = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))

        self.btn_box = toga.Box(style=Pack(direction=ROW))
        self.btn_box.add(self.button)

        self.box_dois.add(self.name_box)
        self.box_dois.add(self.width, self.btn_box, self.height)

        return self.box_dois

    def cria_combo_grupos(self):
        box = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Grupo:', style=Pack(flex=1 / 3, padding=3))
        box.add(button)

        opcoes = []
        opcoes_selection = []

        dados_banco = self.bc_ander.consultar('tab_grupo_produto')

        for itens in dados_banco:
            id_gr = itens['objectId']
            nome_gr = itens['DESCRICAO']

            dados = (id_gr, nome_gr)
            opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_gr = toga.Selection(items=opcoes_selection, on_select=partial(self.atualiza_produto),
                                           style=Pack(flex=1, padding=3))
        box.add(self.selection_gr)

        return box

    def atualiza_produto(self, widget):
        nome_gr_escolhido = widget.value

        self.box_produto.remove(self.selection_prod)

        opcoes = []
        opcoes_selection = []

        id_grupo_escolhido = ''
        dados_banco = self.bc_ander.consultar('tab_grupo_produto')
        for itens in dados_banco:
            nome_grupo = itens['DESCRICAO']

            if nome_gr_escolhido == nome_grupo:
                id_grupo = itens['objectId']
                id_grupo_escolhido = id_grupo

        dados_banco = self.bc_ander.consultar('tab_produto')

        for itens in dados_banco:
            id_prod = itens['objectId']
            nome_prod = itens['DESCRICAO']
            id_gr = itens['ID_GRUPO']

            if id_gr == id_grupo_escolhido:
                dados = (id_prod, nome_prod)
                opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_prod = toga.Selection(items=opcoes_selection, on_select=partial(self.atualiza_label_um_e_saldo),
                                             style=Pack(flex=1, padding=3))
        self.box_produto.add(self.selection_prod)

    def cria_combo_produtos(self):
        self.box_produto = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Produto:', style=Pack(flex=1 / 3, padding=3))
        self.box_produto.add(button)

        opcoes = []
        opcoes_selection = []

        nome_gr_escolhido = self.selection_gr.value

        id_grupo_escolhido = ''
        dados_banco = self.bc_ander.consultar('tab_grupo_produto')
        for itens in dados_banco:
            nome_grupo = itens['DESCRICAO']

            if nome_gr_escolhido == nome_grupo:
                id_grupo = itens['objectId']
                id_grupo_escolhido = id_grupo

        dados_banco = self.bc_ander.consultar('tab_produto')

        for itens in dados_banco:
            id_prod = itens['objectId']
            nome_prod = itens['DESCRICAO']
            id_gr = itens['ID_GRUPO']

            if id_gr == id_grupo_escolhido:
                dados = (id_prod, nome_prod)
                opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_prod = toga.Selection(items=opcoes_selection, on_select=partial(self.atualiza_label_um_e_saldo),
                                             style=Pack(flex=1, padding=3))
        self.box_produto.add(self.selection_prod)

        return self.box_produto

    def atualiza_label_um_e_saldo(self, widget):
        nome_prod_escolhido = widget.value

        self.box_um.remove(self.label_um)
        self.box_saldo.remove(self.label_saldo)

        um_escolhido = ''
        saldo_escolhido = ''

        dados_banco = self.bc_ander.consultar('tab_produto')
        for itens in dados_banco:
            nome_prod = itens['DESCRICAO']

            if nome_prod_escolhido == nome_prod:
                nome_um = itens['UM']
                nome_saldo = itens['ESTOQUE']

                saldo_escolhido = nome_saldo
                um_escolhido = nome_um

        self.label_um = toga.Label(um_escolhido, style=Pack(flex=1))
        self.box_um.add(self.label_um)

        self.label_saldo = toga.Label(saldo_escolhido, style=Pack(flex=1))
        self.box_saldo.add(self.label_saldo)

    def cria_label_um(self):
        self.box_um = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('UM:', style=Pack(flex=1/3, padding_top=13))
        self.box_um.add(button)

        nome_prod_escolhido = self.selection_prod.value
        um_escolhido = ''

        dados_banco = self.bc_ander.consultar('tab_produto')
        for itens in dados_banco:
            nome_prod = itens['DESCRICAO']

            if nome_prod_escolhido == nome_prod:
                nome_um = itens['UM']
                um_escolhido = nome_um

        self.label_um = toga.Label(um_escolhido, style=Pack(flex=1))

        self.box_um.add(self.label_um)

        return self.box_um

    def cria_label_saldo(self):
        self.box_saldo = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Saldo Estoque:', style=Pack(flex=1/3, padding_top=13))
        self.box_saldo.add(button)

        nome_prod_escolhido = self.selection_prod.value
        saldo_escolhido = ''

        dados_banco = self.bc_ander.consultar('tab_produto')
        for itens in dados_banco:
            nome_prod = itens['DESCRICAO']

            if nome_prod_escolhido == nome_prod:
                nome_saldo = itens['ESTOQUE']
                saldo_escolhido = nome_saldo

        self.label_saldo = toga.Label(saldo_escolhido, style=Pack(flex=1))
        self.box_saldo.add(self.label_saldo)

        return self.box_saldo

    def cria_text_data(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Data Entrada:', style=Pack(flex=1/3, padding_top=13))
        box_login.add(button)

        date_mask = "##/##/####"

        self.textinput_data = toga.TextInput(placeholder="DD/MM/AAAA", style=Pack(flex=1),
                                        on_change=self.configura_data)

        self.textinput_data.mask = textwrap.dedent(f"""{date_mask}{date_mask.replace('#', '9')}""")
        box_login.add(self.textinput_data)

        return box_login

    def configura_data(self, widget):
        try:
            input_text = ''.join(filter(str.isdigit, widget.value))

            if len(input_text) >= 8:
                formatted_date = f"{input_text[:2]}/{input_text[2:4]}/{input_text[4:]}"
                if widget.value != formatted_date:
                    widget.value = formatted_date

        except Exception as e:
            print(f"Erro durante o evento on_change: {e}")

    def cria_text_qtde(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Quantidade:', style=Pack(flex=1/3, padding_top=13))
        box_login.add(button)

        self.textinput_qtde = toga.TextInput(placeholder="Quantidade Entrada", style=Pack(flex=1))
        box_login.add(self.textinput_qtde)

        return box_login

    def cria_text_obs(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Observação:', style=Pack(flex=1/3, padding_top=13))
        box_login.add(button)

        self.textinput_obs = toga.TextInput(placeholder="Observação", style=Pack(flex=1))
        box_login.add(self.textinput_obs)

        return box_login

    def cria_btn_salvar(self):
        self.box_btn_finalizar = toga.Box(style=Pack(direction=COLUMN, padding=10))
        self.btn_finalizar = toga.Button('Salvar',
                                         on_press=self.verifica_salvamento,
                                         style=Pack(padding_bottom=5))
        self.box_btn_finalizar.add(self.btn_finalizar)

        return self.box_btn_finalizar

    def cria_btn_voltar_princ(self):
        self.box_btn_principal = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.btn_tela_principal = toga.Button('Ir para Tela Principal',
                                              on_press=self.mostrar_tela_principal,
                                              style=Pack(padding_bottom=5))
        self.box_btn_principal.add(self.btn_tela_principal)

        return self.box_btn_principal

    def cria_box1(self):
        self.box_semifinal1 = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))

        branco = self.cria_espaco_branco()
        branco1 = self.cria_espaco_branco()
        branco2 = self.cria_espaco_branco()
        branco3 = self.cria_espaco_branco()
        branco4 = self.cria_espaco_branco()
        branco5 = self.cria_espaco_branco()
        branco6 = self.cria_espaco_branco()

        titulo = self.cria_titulo()
        combo_gr = self.cria_combo_grupos()
        combo_prod = self.cria_combo_produtos()
        um = self.cria_label_um()
        saldo = self.cria_label_saldo()
        text_data = self.cria_text_data()
        qtde = self.cria_text_qtde()
        obs = self.cria_text_obs()
        salvar = self.cria_btn_salvar()
        btn_principal = self.cria_btn_voltar_princ()

        self.box_semifinal1.add(branco, titulo,
                                branco1, combo_gr,
                                branco2, combo_prod, um, saldo,
                                branco3, text_data,
                                branco4, qtde,
                                branco5, obs,
                                branco6, salvar, btn_principal)

        return self.box_semifinal1

    def startup(self):
        self.main_window.content = self.scroll_container

    def mostrar_tela_principal(self, widget):
        banco = self.bc_ander

        self.tela_principal = TelaPrincipal(self.main_window, banco)
        self.tela_principal.startup()

    def validar_data(self, data_str):
        try:
            data = datetime.strptime(data_str, '%d/%m/%Y')
            data_atual = datetime.now()

            # Verificar se a data é maior que a data atual
            if data > data_atual:
                return None

            # Verificar se a data é mais antiga do que 2 meses além da data atual
            limite_data = data_atual - timedelta(days=60)
            if data < limite_data:
                return None

            return data
        except ValueError:
            return None

    def verifica_salvamento(self, widget):
        if not self.textinput_qtde.value:
            self.main_window.info_dialog("Atenção!", 'O campo "Quantidade" não pode estar vazio!')
        elif not self.textinput_data.value:
            self.main_window.info_dialog("Atenção!", 'O campo "Data" não pode estar vazio!')
        else:
            data_lancada = self.textinput_data.value
            data_str = self.validar_data(data_lancada)

            if data_str:
                self.salvar_entrada(widget)
            else:
                self.main_window.info_dialog("Atenção!", f'A DATA DO MOVIMENTO NÃO DEVE ESTAR:\n'
                                                         f'   - NO FORMATO INCORRETO;\n'
                                                         f'   - MAIOR QUE A DATA ATUAL;\n'
                                                         f'   - MENOR QUE 2 MESES DA DATA ATUAL!')

    def salvar_entrada(self, widget):
        lista_json = []
        dados_post = []

        qtde_str = self.textinput_qtde.value

        saldo_float = float(self.label_saldo.text)

        saldo_atual = saldo_float + float(qtde_str)
        saldo_atual_str = str("%.2f" % saldo_atual)

        data = self.textinput_data.value

        nome_prod_escolhido = self.selection_prod.value
        id_prod_escolhido = ''

        dados_banco = self.bc_ander.consultar('tab_produto')
        for itens in dados_banco:
            nome_prod = itens['DESCRICAO']

            if nome_prod_escolhido == nome_prod:
                id_prod = itens['objectId']
                id_prod_escolhido = id_prod

        if self.textinput_obs.value:
            obs_editado = self.textinput_obs.value
            obs_editado = obs_editado.upper()
        else:
            obs_editado = ''

        print("POST")
        objeto = {"method": "POST", "path": "/classes/entrada",
                  "body": {"ID_PRODUTO": {"__type": "Pointer",
                                          "className": "produto",
                                          "objectId": id_prod_escolhido},
                           "DATA_ENTRADA": data,
                           "QTDE_ENTRADA": qtde_str,
                           "OBS": obs_editado}}
        lista_json.append(objeto)

        dadinhos = (data, id_prod_escolhido, qtde_str, obs_editado)
        dados_post.append(dadinhos)

        pra_atualizar = {"ESTOQUE": saldo_atual_str}

        print("PUT - PRODUTO")
        objeto = {"method": "PUT", "path": f"/classes/produto/{id_prod_escolhido}", "body": pra_atualizar}
        lista_json.append(objeto)

        self.bc_ander.atualizar_por_campo('tab_produto', 'objectId', id_prod_escolhido, pra_atualizar)

        final = 0

        if lista_json:
            final = final + 1
            result = self.conexao.salvar_no_banco(lista_json)
            if dados_post:
                id_entrada_result = result[0]['success']['objectId']
                data_entrada, id_produto, qtde, obs_prod = dados_post[0]

                self.bc_ander.inserir('tab_entrada', {'objectId': id_entrada_result,
                                                      'DATA_ENTRADA': data_entrada,
                                                      'ID_PRODUTO': id_produto,
                                                      'QTDE_ENTRADA': qtde,
                                                      'OBS': obs_prod})

        if final > 0:
            self.mostrar_tela_principal(widget)
            self.main_window.info_dialog("Atenção!", f'DADOS SALVO COM SUCESSO!')
        else:
            self.main_window.info_dialog("Atenção!", f'ALGUM ITEM PRECISA SER\n ALTERADO PARA SALVAR!')


class Saidas:
    def __init__(self, main_window, banco):
        self.bc_ander = banco
        self.conexao = ConexaoBack4App(self.bc_ander)

        self.scroll_container = toga.ScrollContainer(style=Pack(flex=1))
        self.box_final = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))
        box1 = self.cria_box1()
        self.box_final.add(box1)
        self.scroll_container.content = self.box_final

        self.main_window = main_window

    def cria_espaco_branco(self):
        box = toga.Box(style=Pack(direction=ROW))
        button = toga.Label(' ', style=Pack(font_size=10, font_weight='bold'))
        box.add(button)

        return box

    def cria_titulo(self):
        self.box_dois = toga.Box(style=Pack(direction=COLUMN, alignment="center", padding=5))
        self.name_box = toga.Box(style=Pack(direction=ROW))

        self.button = toga.Label('Saída de Produtos', style=Pack(font_size=25, font_weight='bold'))

        self.width = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))
        self.height = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))

        self.btn_box = toga.Box(style=Pack(direction=ROW))
        self.btn_box.add(self.button)

        self.box_dois.add(self.name_box)
        self.box_dois.add(self.width, self.btn_box, self.height)

        return self.box_dois

    def cria_combo_grupos(self):
        box = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Grupo:', style=Pack(flex=1 / 3, padding=3))
        box.add(button)

        opcoes = []
        opcoes_selection = []

        dados_banco = self.bc_ander.consultar('tab_grupo_produto')

        for itens in dados_banco:
            id_gr = itens['objectId']
            nome_gr = itens['DESCRICAO']

            dados = (id_gr, nome_gr)
            opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_gr = toga.Selection(items=opcoes_selection, on_select=partial(self.atualiza_produto),
                                           style=Pack(flex=1, padding=3))
        box.add(self.selection_gr)

        return box

    def atualiza_produto(self, widget):
        nome_gr_escolhido = widget.value

        self.box_produto.remove(self.selection_prod)

        opcoes = []
        opcoes_selection = []

        id_grupo_escolhido = ''
        dados_banco = self.bc_ander.consultar('tab_grupo_produto')
        for itens in dados_banco:
            nome_grupo = itens['DESCRICAO']

            if nome_gr_escolhido == nome_grupo:
                id_grupo = itens['objectId']
                id_grupo_escolhido = id_grupo

        dados_banco = self.bc_ander.consultar('tab_produto')

        for itens in dados_banco:
            id_prod = itens['objectId']
            nome_prod = itens['DESCRICAO']
            id_gr = itens['ID_GRUPO']

            if id_gr == id_grupo_escolhido:
                dados = (id_prod, nome_prod)
                opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_prod = toga.Selection(items=opcoes_selection, on_select=partial(self.atualiza_label_um_e_saldo),
                                             style=Pack(flex=1, padding=3))
        self.box_produto.add(self.selection_prod)

    def cria_combo_produtos(self):
        self.box_produto = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Produto:', style=Pack(flex=1 / 3, padding=3))
        self.box_produto.add(button)

        opcoes = []
        opcoes_selection = []

        nome_gr_escolhido = self.selection_gr.value

        id_grupo_escolhido = ''
        dados_banco = self.bc_ander.consultar('tab_grupo_produto')
        for itens in dados_banco:
            nome_grupo = itens['DESCRICAO']

            if nome_gr_escolhido == nome_grupo:
                id_grupo = itens['objectId']
                id_grupo_escolhido = id_grupo

        dados_banco = self.bc_ander.consultar('tab_produto')

        for itens in dados_banco:
            id_prod = itens['objectId']
            nome_prod = itens['DESCRICAO']
            id_gr = itens['ID_GRUPO']

            if id_gr == id_grupo_escolhido:
                dados = (id_prod, nome_prod)
                opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_prod = toga.Selection(items=opcoes_selection, on_select=partial(self.atualiza_label_um_e_saldo),
                                             style=Pack(flex=1, padding=3))
        self.box_produto.add(self.selection_prod)

        return self.box_produto

    def atualiza_label_um_e_saldo(self, widget):
        nome_prod_escolhido = widget.value

        self.box_um.remove(self.label_um)
        self.box_saldo.remove(self.label_saldo)

        um_escolhido = ''
        saldo_escolhido = ''

        dados_banco = self.bc_ander.consultar('tab_produto')
        for itens in dados_banco:
            nome_prod = itens['DESCRICAO']

            if nome_prod_escolhido == nome_prod:
                nome_um = itens['UM']
                nome_saldo = itens['ESTOQUE']

                saldo_escolhido = nome_saldo
                um_escolhido = nome_um

        self.label_um = toga.Label(um_escolhido, style=Pack(flex=1))
        self.box_um.add(self.label_um)

        self.label_saldo = toga.Label(saldo_escolhido, style=Pack(flex=1))
        self.box_saldo.add(self.label_saldo)

    def cria_label_um(self):
        self.box_um = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('UM:', style=Pack(flex=1/3, padding_top=13))
        self.box_um.add(button)

        nome_prod_escolhido = self.selection_prod.value
        um_escolhido = ''

        dados_banco = self.bc_ander.consultar('tab_produto')
        for itens in dados_banco:
            nome_prod = itens['DESCRICAO']

            if nome_prod_escolhido == nome_prod:
                nome_um = itens['UM']
                um_escolhido = nome_um

        self.label_um = toga.Label(um_escolhido, style=Pack(flex=1))

        self.box_um.add(self.label_um)

        return self.box_um

    def cria_label_saldo(self):
        self.box_saldo = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Saldo Estoque:', style=Pack(flex=1/3, padding_top=13))
        self.box_saldo.add(button)

        nome_prod_escolhido = self.selection_prod.value
        saldo_escolhido = ''

        dados_banco = self.bc_ander.consultar('tab_produto')
        for itens in dados_banco:
            nome_prod = itens['DESCRICAO']

            if nome_prod_escolhido == nome_prod:
                nome_saldo = itens['ESTOQUE']
                saldo_escolhido = nome_saldo

        self.label_saldo = toga.Label(saldo_escolhido, style=Pack(flex=1))
        self.box_saldo.add(self.label_saldo)

        return self.box_saldo

    def cria_text_data(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Data Saída:', style=Pack(flex=1/3, padding_top=13))
        box_login.add(button)

        date_mask = "##/##/####"

        self.textinput_data = toga.TextInput(placeholder="DD/MM/AAAA", style=Pack(flex=1),
                                        on_change=self.configura_data)

        self.textinput_data.mask = textwrap.dedent(f"""{date_mask}{date_mask.replace('#', '9')}""")
        box_login.add(self.textinput_data)

        return box_login

    def configura_data(self, widget):
        try:
            input_text = ''.join(filter(str.isdigit, widget.value))

            if len(input_text) >= 8:
                formatted_date = f"{input_text[:2]}/{input_text[2:4]}/{input_text[4:]}"
                if widget.value != formatted_date:
                    widget.value = formatted_date

        except Exception as e:
            print(f"Erro durante o evento on_change: {e}")

    def cria_text_qtde(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Quantidade:', style=Pack(flex=1/3, padding_top=13))
        box_login.add(button)

        self.textinput_qtde = toga.TextInput(placeholder="Quantidade Saída", style=Pack(flex=1))
        box_login.add(self.textinput_qtde)

        return box_login

    def cria_combo_funcionario(self):
        box = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Funcionário:', style=Pack(flex=1 / 3, padding=3))
        box.add(button)

        opcoes = []
        opcoes_selection = []

        dados_banco = self.bc_ander.consultar('tab_funcionario')

        for itens in dados_banco:
            id_func = itens['objectId']
            nome_func = itens['NOME']

            dados = (id_func, nome_func)
            opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_func = toga.Selection(items=opcoes_selection, style=Pack(flex=1, padding=3))
        box.add(self.selection_func)

        return box

    def cria_text_obs(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Observação:', style=Pack(flex=1/3, padding_top=13))
        box_login.add(button)

        self.textinput_obs = toga.TextInput(placeholder="Observação", style=Pack(flex=1))
        box_login.add(self.textinput_obs)

        return box_login

    def cria_btn_salvar(self):
        self.box_btn_finalizar = toga.Box(style=Pack(direction=COLUMN, padding=10))
        self.btn_finalizar = toga.Button('Salvar',
                                         on_press=self.verifica_salvamento,
                                         style=Pack(padding_bottom=5))
        self.box_btn_finalizar.add(self.btn_finalizar)

        return self.box_btn_finalizar

    def cria_btn_voltar_princ(self):
        self.box_btn_principal = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.btn_tela_principal = toga.Button('Ir para Tela Principal',
                                              on_press=self.mostrar_tela_principal,
                                              style=Pack(padding_bottom=5))
        self.box_btn_principal.add(self.btn_tela_principal)

        return self.box_btn_principal

    def cria_box1(self):
        self.box_semifinal1 = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))

        branco = self.cria_espaco_branco()
        branco1 = self.cria_espaco_branco()
        branco2 = self.cria_espaco_branco()
        branco3 = self.cria_espaco_branco()
        branco4 = self.cria_espaco_branco()
        branco5 = self.cria_espaco_branco()
        branco6 = self.cria_espaco_branco()
        branco7 = self.cria_espaco_branco()

        titulo = self.cria_titulo()
        combo_gr = self.cria_combo_grupos()
        combo_prod = self.cria_combo_produtos()
        um = self.cria_label_um()
        saldo = self.cria_label_saldo()
        text_data = self.cria_text_data()
        qtde = self.cria_text_qtde()
        func = self.cria_combo_funcionario()
        obs = self.cria_text_obs()
        salvar = self.cria_btn_salvar()
        btn_principal = self.cria_btn_voltar_princ()

        self.box_semifinal1.add(branco, titulo,
                                branco1, combo_gr,
                                branco2, combo_prod, um, saldo,
                                branco3, text_data,
                                branco4, qtde,
                                branco5, func,
                                branco6, obs,
                                branco7, salvar, btn_principal)

        return self.box_semifinal1

    def startup(self):
        self.main_window.content = self.scroll_container

    def mostrar_tela_principal(self, widget):
        banco = self.bc_ander

        self.tela_principal = TelaPrincipal(self.main_window, banco)
        self.tela_principal.startup()

    def validar_data(self, data_str):
        try:
            data = datetime.strptime(data_str, '%d/%m/%Y')
            data_atual = datetime.now()

            # Verificar se a data é maior que a data atual
            if data > data_atual:
                return None

            # Verificar se a data é mais antiga do que 2 meses além da data atual
            limite_data = data_atual - timedelta(days=60)
            if data < limite_data:
                return None

            return data
        except ValueError:
            return None

    def verifica_salvamento(self, widget):
        if not self.textinput_qtde.value:
            self.main_window.info_dialog("Atenção!", 'O campo "Quantidade" não pode estar vazio!')
        elif not self.textinput_data.value:
            self.main_window.info_dialog("Atenção!", 'O campo "Data" não pode estar vazio!')
        else:
            qtde = float(self.textinput_qtde.value)
            saldo = float(self.label_saldo.text)
            if qtde > saldo:
                self.main_window.info_dialog("Atenção!", 'Não possui saldo suficiente para este consumo!')
            else:
                data_lancada = self.textinput_data.value
                data_str = self.validar_data(data_lancada)

                if data_str:
                    self.salvar_saida(widget)
                else:
                    self.main_window.info_dialog("Atenção!", f'A DATA DO MOVIMENTO NÃO DEVE ESTAR:\n'
                                                             f'   - NO FORMATO INCORRETO;\n'
                                                             f'   - MAIOR QUE A DATA ATUAL;\n'
                                                             f'   - MENOR QUE 2 MESES DA DATA ATUAL!')

    def salvar_saida(self, widget):
        lista_json = []
        dados_post = []

        qtde_str = self.textinput_qtde.value

        saldo_float = float(self.label_saldo.text)

        saldo_atual = saldo_float - float(qtde_str)
        saldo_atual_str = str("%.2f" % saldo_atual)

        data = self.textinput_data.value

        nome_prod_escolhido = self.selection_prod.value
        id_prod_escolhido = ''

        dados_banco = self.bc_ander.consultar('tab_produto')
        for itens in dados_banco:
            nome_prod = itens['DESCRICAO']

            if nome_prod_escolhido == nome_prod:
                id_prod = itens['objectId']
                id_prod_escolhido = id_prod

        nome_func_escolhido = self.selection_func.value
        id_func_escolhido = ''

        dados_func = self.bc_ander.consultar('tab_funcionario')
        for itens in dados_func:
            nome_func = itens['NOME']

            if nome_func_escolhido == nome_func:
                id_func = itens['objectId']
                id_func_escolhido = id_func

        if self.textinput_obs.value:
            obs_editado = self.textinput_obs.value
            obs_editado = obs_editado.upper()
        else:
            obs_editado = ''

        print("POST")
        objeto = {"method": "POST", "path": "/classes/saida",
                  "body": {"ID_PRODUTO": {"__type": "Pointer",
                                          "className": "produto",
                                          "objectId": id_prod_escolhido},
                           "ID_FUNCIONARIO": {"__type": "Pointer",
                                          "className": "funcionario",
                                          "objectId": id_func_escolhido},
                           "DATA_SAIDA": data,
                           "QTDE_SAIDA": qtde_str,
                           "OBS": obs_editado}}
        lista_json.append(objeto)

        dadinhos = (data, id_prod_escolhido, qtde_str, obs_editado, id_func_escolhido)
        dados_post.append(dadinhos)

        pra_atualizar = {"ESTOQUE": saldo_atual_str}

        print("PUT - PRODUTO")
        objeto = {"method": "PUT", "path": f"/classes/produto/{id_prod_escolhido}", "body": pra_atualizar}
        lista_json.append(objeto)

        self.bc_ander.atualizar_por_campo('tab_produto', 'objectId', id_prod_escolhido, pra_atualizar)

        final = 0

        if lista_json:
            final = final + 1
            result = self.conexao.salvar_no_banco(lista_json)
            if dados_post:
                id_saida_result = result[0]['success']['objectId']
                data_saida, id_produto, qtde, obs_prod, id_func = dados_post[0]

                self.bc_ander.inserir('tab_saida', {'objectId': id_saida_result,
                                                    'DATA_SAIDA': data_saida,
                                                    'ID_PRODUTO': id_produto,
                                                    'ID_FUNCIONARIO': id_func,
                                                    'QTDE_SAIDA': qtde,
                                                    'OBS': obs_prod})

        if final > 0:
            self.mostrar_tela_principal(widget)
            self.main_window.info_dialog("Atenção!", f'DADOS SALVO COM SUCESSO!')
        else:
            self.main_window.info_dialog("Atenção!", f'ALGUM ITEM PRECISA SER\n ALTERADO PARA SALVAR!')


class Estoque:
    def __init__(self, main_window, banco):
        self.bc_ander = banco
        self.conexao = ConexaoBack4App(self.bc_ander)

        self.scroll_container = toga.ScrollContainer(style=Pack(flex=1))
        self.box_final = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))
        box1 = self.cria_box1()
        self.box_final.add(box1)
        self.scroll_container.content = self.box_final

        self.main_window = main_window

    def cria_espaco_branco(self):
        box = toga.Box(style=Pack(direction=ROW))
        button = toga.Label(' ', style=Pack(font_size=10, font_weight='bold'))
        box.add(button)

        return box

    def cria_titulo(self):
        self.box_dois = toga.Box(style=Pack(direction=COLUMN, alignment="center", padding=5))
        self.name_box = toga.Box(style=Pack(direction=ROW))

        self.button = toga.Label('Estoque de Produtos', style=Pack(font_size=25, font_weight='bold'))

        self.width = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))
        self.height = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))

        self.btn_box = toga.Box(style=Pack(direction=ROW))
        self.btn_box.add(self.button)

        self.box_dois.add(self.name_box)
        self.box_dois.add(self.width, self.btn_box, self.height)

        return self.box_dois

    def cria_combo_grupos(self):
        box = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Grupo:', style=Pack(flex=1 / 3, padding=3))
        box.add(button)

        opcoes = []
        opcoes_selection = []

        dados = ("00", "TODOS")
        opcoes.append(dados)

        dados_banco = self.bc_ander.consultar('tab_grupo_produto')

        for itens in dados_banco:
            id_gr = itens['objectId']
            nome_gr = itens['DESCRICAO']

            dados = (id_gr, nome_gr)
            opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_gr = toga.Selection(items=opcoes_selection,
                                           style=Pack(flex=1, padding=3))
        box.add(self.selection_gr)

        return box

    def cria_btn_consulta(self):
        box_btn_finalizar = toga.Box(style=Pack(direction=COLUMN, padding=10))
        btn_finalizar = toga.Button('Consultar',
                                         on_press=self.consulta_est,
                                         style=Pack(padding_bottom=5))
        box_btn_finalizar.add(btn_finalizar)

        return box_btn_finalizar

    def tabela_estoque(self):
        lista_para_tabela = []

        dados_produtos = self.bc_ander.consultar('tab_produto')

        for dados in dados_produtos:
            nome_prod = dados['DESCRICAO']
            um_prod = dados['UM']
            estoque_prod = dados['ESTOQUE']
            id_gr = dados['ID_GRUPO']

            dados_gr = self.bc_ander.consultar_cond('tab_grupo_produto', 'objectId', id_gr)
            nome_gr = dados_gr[0]['DESCRICAO']

            dados = (nome_prod, nome_gr, um_prod, estoque_prod)
            lista_para_tabela.append(dados)

        locale.setlocale(locale.LC_ALL, '')
        dados_tabela_ordenados = sorted(lista_para_tabela, key=lambda x: locale.strxfrm(x[0]))

        self.tabela = toga.Table(
            headings=['Produto', 'Grupo', 'UM', 'Qtde'],
            data=dados_tabela_ordenados, missing_value='', style=Pack(flex=1))

        return self.tabela

    def atualiza_tabela_estoque(self):
        lista_para_tabela = []

        dados_produtos = self.bc_ander.consultar('tab_produto')

        nome_gr = self.selection_gr.value

        for dados in dados_produtos:
            nome_prod = dados['DESCRICAO']
            um_prod = dados['UM']
            estoque_prod = dados['ESTOQUE']
            id_gr = dados['ID_GRUPO']

            dados_gr = self.bc_ander.consultar_cond('tab_grupo_produto', 'objectId', id_gr)
            nome_grupo = dados_gr[0]['DESCRICAO']

            if nome_gr != "TODOS":
                if nome_grupo == nome_gr:
                    dados = (nome_prod, nome_grupo, um_prod, estoque_prod)
                    lista_para_tabela.append(dados)
            else:
                dados = (nome_prod, nome_grupo, um_prod, estoque_prod)
                lista_para_tabela.append(dados)

        locale.setlocale(locale.LC_ALL, '')
        dados_tabela_ordenados = sorted(lista_para_tabela, key=lambda x: locale.strxfrm(x[0]))

        self.tabela.data = dados_tabela_ordenados

    def cria_btn_voltar_princ(self):
        self.box_btn_principal = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.btn_tela_principal = toga.Button('Ir para Tela Principal',
                                              on_press=self.mostrar_tela_principal,
                                              style=Pack(padding_bottom=5))
        self.box_btn_principal.add(self.btn_tela_principal)

        return self.box_btn_principal

    def cria_box1(self):
        self.box_semifinal1 = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))

        branco = self.cria_espaco_branco()
        branco1 = self.cria_espaco_branco()
        branco2 = self.cria_espaco_branco()
        branco3 = self.cria_espaco_branco()

        titulo = self.cria_titulo()
        grupos = self.cria_combo_grupos()
        consulta = self.cria_btn_consulta()
        tabela = self.tabela_estoque()
        btn_principal = self.cria_btn_voltar_princ()

        self.box_semifinal1.add(branco, titulo,
                                branco1, grupos,
                                branco2, consulta,
                                branco3, tabela, btn_principal)

        return self.box_semifinal1

    def startup(self):
        self.main_window.content = self.scroll_container

    def consulta_est(self, widget):
        grupo_selecionado = self.selection_gr.value

        self.atualiza_tabela_estoque()

    def mostrar_tela_principal(self, widget):
        banco = self.bc_ander

        self.tela_principal = TelaPrincipal(self.main_window, banco)
        self.tela_principal.startup()


class Movimentacao:
    def __init__(self, main_window, banco):
        self.bc_ander = banco
        self.conexao = ConexaoBack4App(self.bc_ander)

        self.scroll_container = toga.ScrollContainer(style=Pack(flex=1))
        self.box_final = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))
        box1 = self.cria_box1()
        self.box_final.add(box1)
        self.scroll_container.content = self.box_final

        self.main_window = main_window

    def cria_espaco_branco(self):
        box = toga.Box(style=Pack(direction=ROW))
        button = toga.Label(' ', style=Pack(font_size=10, font_weight='bold'))
        box.add(button)

        return box

    def cria_titulo(self):
        self.box_dois = toga.Box(style=Pack(direction=COLUMN, alignment="center", padding=5))
        self.name_box = toga.Box(style=Pack(direction=ROW))

        self.button = toga.Label('Movimentação do Estoque', style=Pack(font_size=25, font_weight='bold'))

        self.width = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))
        self.height = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))

        self.btn_box = toga.Box(style=Pack(direction=ROW))
        self.btn_box.add(self.button)

        self.box_dois.add(self.name_box)
        self.box_dois.add(self.width, self.btn_box, self.height)

        return self.box_dois

    def cria_text_data_inicial(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Data Inicial:', style=Pack(flex=1/3, padding_top=13))
        box_login.add(button)

        data_atual = date.today()
        data_inicial = data_atual.replace(day=1).strftime("%d/%m/%Y")

        self.textinput_data_ini = toga.TextInput(value=data_inicial, placeholder="DD/MM/AAAA", style=Pack(flex=1),
                                        on_change=self.configura_data)

        date_mask = "##/##/####"
        self.textinput_data_ini.mask = textwrap.dedent(f"""{date_mask}{date_mask.replace('#', '9')}""")
        box_login.add(self.textinput_data_ini)

        return box_login

    def cria_text_data_final(self):
        box_login = toga.Box(style=Pack(direction=ROW))

        button = toga.Label('Data Final:', style=Pack(flex=1/3, padding_top=13))
        box_login.add(button)

        data_atual = date.today()
        data_final = data_atual.strftime("%d/%m/%Y")

        self.textinput_data_fim = toga.TextInput(value=data_final, placeholder="DD/MM/AAAA", style=Pack(flex=1),
                                        on_change=self.configura_data)

        date_mask = "##/##/####"

        self.textinput_data_fim.mask = textwrap.dedent(f"""{date_mask}{date_mask.replace('#', '9')}""")
        box_login.add(self.textinput_data_fim)

        return box_login

    def configura_data(self, widget):
        try:
            input_text = ''.join(filter(str.isdigit, widget.value))

            if len(input_text) >= 8:
                formatted_date = f"{input_text[:2]}/{input_text[2:4]}/{input_text[4:]}"
                if widget.value != formatted_date:
                    widget.value = formatted_date

        except Exception as e:
            print(f"Erro durante o evento on_change: {e}")

    def cria_combo_grupos(self):
        box = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Grupo:', style=Pack(flex=1 / 3, padding=3))
        box.add(button)

        opcoes = []
        opcoes_selection = []

        dados = ("00", "TODOS")
        opcoes.append(dados)

        dados_banco = self.bc_ander.consultar('tab_grupo_produto')

        for itens in dados_banco:
            id_gr = itens['objectId']
            nome_gr = itens['DESCRICAO']

            dados = (id_gr, nome_gr)
            opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_gr = toga.Selection(items=opcoes_selection, on_select=partial(self.atualiza_produto),
                                           style=Pack(flex=1, padding=3))
        box.add(self.selection_gr)

        return box

    def atualiza_produto(self, widget):
        nome_gr_escolhido = widget.value

        self.box_produto.remove(self.selection_prod)

        opcoes = []
        opcoes_selection = []

        dados = ("00", "TODOS")
        opcoes.append(dados)

        id_grupo_escolhido = ''
        dados_banco = self.bc_ander.consultar('tab_grupo_produto')
        for itens in dados_banco:
            nome_grupo = itens['DESCRICAO']

            if nome_gr_escolhido == nome_grupo:
                id_grupo = itens['objectId']
                id_grupo_escolhido = id_grupo

        dados_banco = self.bc_ander.consultar('tab_produto')

        for itens in dados_banco:
            id_prod = itens['objectId']
            nome_prod = itens['DESCRICAO']
            id_gr = itens['ID_GRUPO']

            if id_gr == id_grupo_escolhido:
                dados = (id_prod, nome_prod)
                opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_prod = toga.Selection(items=opcoes_selection, style=Pack(flex=1, padding=3))
        self.box_produto.add(self.selection_prod)

    def cria_combo_produtos(self):
        self.box_produto = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Produto:', style=Pack(flex=1 / 3, padding=3))
        self.box_produto.add(button)

        opcoes = []
        opcoes_selection = []

        dados = ("00", "TODOS")
        opcoes.append(dados)

        dados_banco = self.bc_ander.consultar('tab_produto')
        for itens in dados_banco:
            id_prod = itens['objectId']
            nome_prod = itens['DESCRICAO']

            dados = (id_prod, nome_prod)
            opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_prod = toga.Selection(items=opcoes_selection, style=Pack(flex=1, padding=3))
        self.box_produto.add(self.selection_prod)

        return self.box_produto

    def cria_combo_funcionario(self):
        box = toga.Box(style=Pack(direction=ROW, padding_top=12))

        button = toga.Label('Funcionário:', style=Pack(flex=1 / 3, padding=3))
        box.add(button)

        opcoes = []
        opcoes_selection = []

        dados = ("00", "TODOS")
        opcoes.append(dados)

        dados_banco = self.bc_ander.consultar('tab_funcionario')

        for itens in dados_banco:
            id_func = itens['objectId']
            nome_func = itens['NOME']

            dados = (id_func, nome_func)
            opcoes.append(dados)

        for item_opcao in opcoes:
            objectid, descricao = item_opcao
            opcoes_selection.append(descricao)

        self.selection_func = toga.Selection(items=opcoes_selection, style=Pack(flex=1, padding=3))
        box.add(self.selection_func)

        return box

    def cria_btn_consulta(self):
        box_btn_finalizar = toga.Box(style=Pack(direction=COLUMN, padding=10))
        btn_finalizar = toga.Button('Consultar',
                                         on_press=self.consulta_mov,
                                         style=Pack(padding_bottom=5))
        box_btn_finalizar.add(btn_finalizar)

        return box_btn_finalizar

    def cria_btn_voltar_princ(self):
        self.box_btn_principal = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.btn_tela_principal = toga.Button('Ir para Tela Principal',
                                              on_press=self.mostrar_tela_principal,
                                              style=Pack(padding_bottom=5))
        self.box_btn_principal.add(self.btn_tela_principal)

        return self.box_btn_principal

    def cria_box1(self):
        box_semifinal1 = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))

        branco = self.cria_espaco_branco()
        branco1 = self.cria_espaco_branco()
        branco2 = self.cria_espaco_branco()
        branco3 = self.cria_espaco_branco()
        branco4 = self.cria_espaco_branco()
        branco5 = self.cria_espaco_branco()
        branco6 = self.cria_espaco_branco()
        branco7 = self.cria_espaco_branco()

        titulo = self.cria_titulo()
        data_ini = self.cria_text_data_inicial()
        data_fim = self.cria_text_data_final()
        grupos = self.cria_combo_grupos()
        produtos = self.cria_combo_produtos()
        funcionario = self.cria_combo_funcionario()
        consulta = self.cria_btn_consulta()
        btn_principal = self.cria_btn_voltar_princ()

        box_semifinal1.add(branco, titulo,
                                branco1, data_ini,
                                branco2, data_fim,
                                branco3, grupos,
                                branco4, produtos,
                                branco5, funcionario,
                                branco6, consulta,
                                branco7, btn_principal)

        return box_semifinal1

    def startup(self):
        self.main_window.content = self.scroll_container

    def consulta_mov(self, widget):
        data_ini = self.textinput_data_ini.value
        data_fim = self.textinput_data_fim.value

        nome_gr = self.selection_gr.value
        nome_prod = self.selection_prod.value
        nome_func = self.selection_func.value

        banco = self.bc_ander

        self.tela_tabela_mov = TabelaMov(self.main_window, banco, data_ini, data_fim, nome_gr, nome_prod, nome_func)
        self.tela_tabela_mov.startup()

    def mostrar_tela_principal(self, widget):
        banco = self.bc_ander

        self.tela_principal = TelaPrincipal(self.main_window, banco)
        self.tela_principal.startup()


class TabelaMov:
    def __init__(self, main_window, banco, data_ini, data_fim, nome_gr, nome_prod, nome_func):
        self.bc_ander = banco
        self.conexao = ConexaoBack4App(self.bc_ander)

        self.data_ini = data_ini
        self.data_fim = data_fim

        self.nome_gr = nome_gr
        self.nome_prod = nome_prod
        self.nome_func = nome_func

        self.scroll_container = toga.ScrollContainer(style=Pack(flex=1))
        self.box_final = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))
        box1 = self.cria_box1()
        self.box_final.add(box1)
        self.scroll_container.content = self.box_final

        self.main_window = main_window

    def cria_espaco_branco(self):
        box = toga.Box(style=Pack(direction=ROW))
        button = toga.Label(' ', style=Pack(font_size=10, font_weight='bold'))
        box.add(button)

        return box

    def cria_titulo(self):
        self.box_dois = toga.Box(style=Pack(direction=COLUMN, alignment="center", padding=5))
        self.name_box = toga.Box(style=Pack(direction=ROW))

        self.button = toga.Label('Movimentação do Estoque', style=Pack(font_size=25, font_weight='bold'))

        self.width = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))
        self.height = toga.Label(f'', style=Pack(font_size=5, font_weight='bold'))

        self.btn_box = toga.Box(style=Pack(direction=ROW))
        self.btn_box.add(self.button)

        self.box_dois.add(self.name_box)
        self.box_dois.add(self.width, self.btn_box, self.height)

        return self.box_dois

    def tabela_mov(self):
        dados_tabela = []
        dados_entrada = self.bc_ander.consultar_entre_datas('tab_entrada', 'DATA_ENTRADA', self.data_ini, self.data_fim)
        for itens in dados_entrada:
            data_ent = itens['DATA_ENTRADA']
            id_prod_ent = itens['ID_PRODUTO']
            qtde_ent = itens['QTDE_ENTRADA']

            dados_prod = self.bc_ander.consultar_cond('tab_produto', 'objectId', id_prod_ent)
            nome_prod = dados_prod[0]['DESCRICAO']
            um_prod = dados_prod[0]['UM']

            nome_func = ''
            qtde_sai = ''

            dudu = (data_ent, nome_prod, um_prod, qtde_ent, qtde_sai, nome_func)
            dados_tabela.append(dudu)

        dados_saida = self.bc_ander.consultar_entre_datas('tab_saida', 'DATA_SAIDA', self.data_ini, self.data_fim)
        for itens1 in dados_saida:
            data_sai = itens1['DATA_SAIDA']
            id_prod_sai = itens1['ID_PRODUTO']
            id_func_sai = itens1['ID_FUNCIONARIO']
            qtde_sai = itens1['QTDE_SAIDA']
            qtde_neg = "-" + qtde_sai

            dados_func = self.bc_ander.consultar_cond('tab_funcionario', 'objectId', id_func_sai)
            nome_func = dados_func[0]['NOME']

            dados_prod = self.bc_ander.consultar_cond('tab_produto', 'objectId', id_prod_sai)
            nome_prod = dados_prod[0]['DESCRICAO']
            um_prod = dados_prod[0]['UM']

            qtde_entr = ''

            dudu = (data_sai, nome_prod, um_prod, qtde_entr, qtde_neg, nome_func)
            dados_tabela.append(dudu)

        dados_tabela_ordenados = sorted(dados_tabela, key=lambda x: datetime.strptime(x[0], '%d/%m/%Y'))

        lista_nova = []

        if self.nome_func != "TODOS" and self.nome_gr != "TODOS" and self.nome_prod != "TODOS":
            for dadus in dados_tabela_ordenados:
                data, prod, um, qtde_ent, qtde_sai, func = dadus
                if self.nome_prod == prod and self.nome_func == func:
                    didi = (data, prod, um, qtde_ent, qtde_sai, func)
                    lista_nova.append(didi)

        elif self.nome_func == "TODOS" and self.nome_gr != "TODOS" and self.nome_prod != "TODOS":
            for dadus in dados_tabela_ordenados:
                data, prod, um, qtde_ent, qtde_sai, func = dadus
                if self.nome_prod == prod:
                    didi = (data, prod, um, qtde_ent, qtde_sai, func)
                    lista_nova.append(didi)

        elif self.nome_func == "TODOS" and self.nome_gr != "TODOS" and self.nome_prod == "TODOS":
            for dadus in dados_tabela_ordenados:
                data, prod, um, qtde_ent, qtde_sai, func = dadus
                if self.nome_gr == grupo:
                    didi = (data, prod, um, qtde_ent, qtde_sai, func)
                    lista_nova.append(didi)

        elif self.nome_func != "TODOS" and self.nome_gr != "TODOS" and self.nome_prod == "TODOS":
            for dadus in dados_tabela_ordenados:
                data, prod, um, qtde_ent, qtde_sai, func = dadus
                if self.nome_gr == grupo and self.nome_func == func:
                    didi = (data, prod, um, qtde_ent, qtde_sai, func)
                    lista_nova.append(didi)

        elif self.nome_func != "TODOS" and self.nome_gr == "TODOS" and self.nome_prod == "TODOS":
            for dadus in dados_tabela_ordenados:
                data, prod, um, qtde_ent, qtde_sai, func = dadus
                if self.nome_func == func:
                    didi = (data, prod, um, qtde_ent, qtde_sai, func)
                    lista_nova.append(didi)

        else:
            lista_nova = dados_tabela_ordenados

        self.tabela = toga.Table(
            headings=['Data', 'Produto', 'UM', 'Entrad', 'Saída', 'Funcionário'],
            data=lista_nova, missing_value='', style=Pack(flex=1))

        return self.tabela

    def cria_btn_voltar_princ(self):
        self.box_btn_principal = toga.Box(style=Pack(direction=COLUMN, padding=10))

        self.btn_tela_principal = toga.Button('Ir para Tela Principal',
                                              on_press=self.mostrar_tela_principal,
                                              style=Pack(padding_bottom=5))
        self.box_btn_principal.add(self.btn_tela_principal)

        return self.box_btn_principal

    def cria_box1(self):
        box_semifinal1 = toga.Box(style=Pack(direction=COLUMN, padding=1, flex=1))

        branco = self.cria_espaco_branco()
        branco1 = self.cria_espaco_branco()

        titulo = self.cria_titulo()
        tabela = self.tabela_mov()
        btn_principal = self.cria_btn_voltar_princ()

        box_semifinal1.add(branco, titulo, branco1, tabela, btn_principal)

        return box_semifinal1

    def startup(self):
        self.main_window.content = self.scroll_container

    def consulta_mov(self, widget):
        data_ini = self.textinput_data_ini.value
        data_fim = self.textinput_data_fim.value

        self.atualiza_tabela_mov(data_ini, data_fim)

    def mostrar_tela_principal(self, widget):
        banco = self.bc_ander

        self.tela_principal = TelaPrincipal(self.main_window, banco)
        self.tela_principal.startup()


def main():
    return EstoquePolicar()

if __name__ == '__main__':
    main().main_loop()
