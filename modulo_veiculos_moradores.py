import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import pathlib
import os

# Configuração de Caminhos Unificados do SISADAM
PASTA_BASE = pathlib.Path.home() / "Documents" / "SISADAM"
PASTA_BANCO = PASTA_BASE / "Arquivos_Banco"
ARQUIVO_DB = PASTA_BANCO / "veiculos_moradores.db"

class BancoVeiculosMoradores(ctk.CTkFrame):
    def __init__(self, master, nivel="OPERADOR", **kwargs):
        super().__init__(master, **kwargs)
        self.cor_destaque = "#F57C00" 
        self.id_em_edicao = None
        self.nivel = nivel 
        
        PASTA_BANCO.mkdir(parents=True, exist_ok=True)
        
        self.criar_banco()
        self.montar_interface()
        self.aplicar_permissoes()
        self.carregar_dados()

    def criar_banco(self):
        conn = sqlite3.connect(str(ARQUIVO_DB))
        conn.execute('''CREATE TABLE IF NOT EXISTS veiculos_moradores (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            morador TEXT, 
                            apartamento TEXT,
                            bloco TEXT,
                            marca TEXT,
                            modelo TEXT,
                            tipo TEXT,
                            cor TEXT,
                            placa TEXT,
                            vaga_garagem TEXT,
                            tamanho_vaga TEXT)''')
        
        try:
            conn.execute("ALTER TABLE veiculos_moradores ADD COLUMN tamanho_vaga TEXT")
        except sqlite3.OperationalError:
            pass 
            
        conn.commit()
        conn.close()

    def montar_interface(self):
        self.label_titulo = ctk.CTkLabel(self, text=f"Cadastro - Veículos de Condutores [{self.nivel}]", font=("Roboto Mono", 24, "bold"), text_color=self.cor_destaque)
        self.label_titulo.pack(pady=15)

        # --- QUADRO DE FORMULÁRIO ---
        self.frame_form = ctk.CTkFrame(self, fg_color="#121212", corner_radius=12, border_width=1, border_color="#333333")
        self.frame_form.pack(pady=10, padx=20, fill="x")

        # LINHA 1 (Imóvel e Vaga)
        self.ent_bloco = ctk.CTkComboBox(self.frame_form, values=["BLOCO A", "BLOCO B"], width=100)
        self.ent_bloco.set("BLOCO")
        self.ent_bloco.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.ent_apt = ctk.CTkEntry(self.frame_form, placeholder_text="APTO", width=80)
        self.ent_apt.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.ent_vaga = ctk.CTkEntry(self.frame_form, placeholder_text="Nº DA VAGA", width=120)
        self.ent_vaga.grid(row=0, column=2, padx=10, pady=10, sticky="w")

        self.ent_tamanho_vaga = ctk.CTkComboBox(self.frame_form, values=["PEQUENA", "MÉDIA", "GRANDE"], width=140)
        self.ent_tamanho_vaga.set("TAMANHO VAGA")
        self.ent_tamanho_vaga.grid(row=0, column=3, padx=10, pady=10, sticky="w")

        # LINHA 2 (Veículo)
        self.frame_veiculo = ctk.CTkFrame(self.frame_form, fg_color="transparent")
        self.frame_veiculo.grid(row=1, column=0, columnspan=4, padx=10, pady=(0, 10), sticky="w")

        self.ent_marca = ctk.CTkEntry(self.frame_veiculo, placeholder_text="MARCA", width=120)
        self.ent_marca.pack(side="left", padx=(0, 10))

        self.ent_modelo = ctk.CTkEntry(self.frame_veiculo, placeholder_text="MODELO", width=150)
        self.ent_modelo.pack(side="left", padx=(0, 10))

        self.ent_tipo = ctk.CTkComboBox(self.frame_veiculo, values=["AUTOMÓVEL", "PICKUP", "SUV", "MOTO"], width=150)
        self.ent_tipo.set("TIPO")
        self.ent_tipo.pack(side="left", padx=(0, 10))

        self.ent_cor = ctk.CTkEntry(self.frame_veiculo, placeholder_text="COR", width=100)
        self.ent_cor.pack(side="left", padx=(0, 10))

        self.ent_placa = ctk.CTkEntry(self.frame_veiculo, placeholder_text="PLACA", width=120)
        self.ent_placa.pack(side="left")

        # LINHA 3 (Nome do Condutor)
        self.ent_condutor = ctk.CTkEntry(self.frame_form, placeholder_text="NOME DO CONDUTOR", width=350)
        self.ent_condutor.grid(row=2, column=0, columnspan=4, padx=10, pady=(0, 10), sticky="w")

        # --- BARRA DE AÇÕES ---
        self.frame_acoes = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_acoes.pack(pady=10, padx=20, fill="x")

        # NOVO BOTÃO: NOVO REGISTRO
        self.btn_novo = ctk.CTkButton(self.frame_acoes, text="+ NOVO REGISTRO", fg_color="#2E7D32", hover_color="#1B5E20", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.reset_total, width=150)
        self.btn_novo.pack(side="left", padx=5)

        self.btn_salvar = ctk.CTkButton(self.frame_acoes, text="SALVAR REGISTRO", fg_color=self.cor_destaque, text_color="black", font=("Roboto Mono", 12, "bold"), command=self.salvar_registro, width=150)
        self.btn_salvar.pack(side="left", padx=5)

        self.btn_editar = ctk.CTkButton(self.frame_acoes, text="EDITAR REGISTRO", fg_color="#1E88E5", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.carregar_edicao, width=150)
        self.btn_editar.pack(side="left", padx=5)

        self.btn_deletar = ctk.CTkButton(self.frame_acoes, text="DELETAR", fg_color="#D32F2F", hover_color="#B71C1C", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.deletar_registro, width=100)
        self.btn_deletar.pack(side="right", padx=5)

        self.btn_exportar = ctk.CTkButton(self.frame_acoes, text="📊 EXPORTAR PLANILHA", fg_color="#1D6F42", hover_color="#144C2D", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.exportar_relatorio, width=200)
        self.btn_exportar.pack(side="right", padx=5)

        self.btn_limpar = ctk.CTkButton(self.frame_acoes, text="LIMPAR", fg_color="#757575", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.limpar_campos, width=100)
        self.btn_limpar.pack(side="right", padx=5)

        # --- TABELA DE VISUALIZAÇÃO ---
        self.frame_tabela = ctk.CTkFrame(self)
        self.frame_tabela.pack(pady=10, padx=20, fill="both", expand=True)

        colunas = ("ID", "Apto", "Bloco", "Marca", "Modelo", "Tipo", "Cor", "Placa", "Vaga", "Tam. Vaga", "Condutor")
        self.tabela = ttk.Treeview(self.frame_tabela, columns=colunas, show="headings")
        
        for col in colunas:
            self.tabela.heading(col, text=col)
            if col == "Condutor": largura = 250
            elif col in ["Marca", "Modelo", "Vaga"]: largura = 110
            elif col == "Tam. Vaga": largura = 90
            elif col in ["ID", "Apto", "Cor"]: largura = 50
            elif col in ["Bloco", "Placa"]: largura = 80
            else: largura = 100
            self.tabela.column(col, width=largura, anchor="center")
            
        self.tabela.pack(fill="both", expand=True, padx=10, pady=10)

    def aplicar_permissoes(self):
        cor_bloqueado = "#444444"
        if self.nivel == "OPERADOR":
            self.btn_editar.configure(state="disabled", fg_color=cor_bloqueado)
            self.btn_deletar.configure(state="disabled", fg_color=cor_bloqueado)
            self.btn_exportar.configure(state="disabled", fg_color=cor_bloqueado)
        elif self.nivel == "ADMIN":
            self.btn_editar.configure(state="disabled", fg_color=cor_bloqueado)
            self.btn_deletar.configure(state="disabled", fg_color=cor_bloqueado)

    def reset_total(self):
        """Limpa campos e reseta os menus de seleção para o estado inicial"""
        self.limpar_campos()
        self.ent_bloco.set("BLOCO")
        self.ent_tipo.set("TIPO")
        self.ent_tamanho_vaga.set("TAMANHO VAGA")
        self.id_em_edicao = None
        self.btn_salvar.configure(text="SALVAR REGISTRO")

    def salvar_registro(self):
        dados = (
            self.ent_condutor.get().strip().upper(),
            self.ent_apt.get().strip().upper(),
            self.ent_bloco.get() if self.ent_bloco.get() != "BLOCO" else "",
            self.ent_marca.get().strip().upper(),
            self.ent_modelo.get().strip().upper(),
            self.ent_tipo.get() if self.ent_tipo.get() != "TIPO" else "",
            self.ent_cor.get().strip().upper(),
            self.ent_placa.get().strip().upper(),
            self.ent_vaga.get().strip().upper(),
            self.ent_tamanho_vaga.get() if self.ent_tamanho_vaga.get() != "TAMANHO VAGA" else ""
        )

        if not dados[0] or not dados[7]:
            messagebox.showwarning("Aviso", "Preencha obrigatoriamente NOME DO CONDUTOR e PLACA.")
            return

        conn = sqlite3.connect(str(ARQUIVO_DB))
        if self.id_em_edicao:
            if self.nivel != "MASTER":
                messagebox.showerror("Bloqueado", "Apenas contas MASTER podem alterar registros.")
                conn.close()
                return
                
            conn.execute('''UPDATE veiculos_moradores SET morador=?, apartamento=?, bloco=?, marca=?, modelo=?, tipo=?, cor=?, placa=?, vaga_garagem=?, tamanho_vaga=? WHERE id=?''', 
                         (*dados, self.id_em_edicao))
            messagebox.showinfo("Sucesso", "Registro atualizado.")
        else:
            conn.execute('''INSERT INTO veiculos_moradores (morador, apartamento, bloco, marca, modelo, tipo, cor, placa, vaga_garagem, tamanho_vaga) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', dados)
            messagebox.showinfo("Sucesso", "Veículo cadastrado com sucesso!")
            
        conn.commit()
        conn.close()
        self.reset_total()
        self.carregar_dados()

    def carregar_edicao(self):
        if self.nivel != "MASTER":
            messagebox.showerror("Acesso Negado", "Você não tem permissão para editar registros.")
            return

        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um registro na tabela para editar.")
            return
            
        valores = self.tabela.item(selecionado[0])['values']
        self.id_em_edicao = valores[0]
        
        self.limpar_campos()
        self.ent_apt.insert(0, str(valores[1]) if str(valores[1]) != "-" else "")
        self.ent_bloco.set(valores[2] if str(valores[2]) != "-" else "BLOCO")
        self.ent_marca.insert(0, valores[3])
        self.ent_modelo.insert(0, valores[4])
        self.ent_tipo.set(valores[5] if str(valores[5]) != "-" else "TIPO")
        self.ent_cor.insert(0, valores[6])
        self.ent_placa.insert(0, valores[7])
        self.ent_vaga.insert(0, str(valores[8]) if str(valores[8]) != "-" else "")
        self.ent_tamanho_vaga.set(valores[9] if str(valores[9]) != "-" else "TAMANHO VAGA")
        self.ent_condutor.insert(0, valores[10])
        
        self.btn_salvar.configure(text="ATUALIZAR DADOS")

    def deletar_registro(self):
        if self.nivel != "MASTER":
            messagebox.showerror("Acesso Negado", "Você não tem permissão para excluir registros.")
            return

        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione o registro para excluir.")
            return
            
        if messagebox.askyesno("Confirmar", "Deseja apagar permanentemente este registro de veículo?"):
            conn = sqlite3.connect(str(ARQUIVO_DB))
            id_registro = self.tabela.item(selecionado[0])['values'][0]
            conn.execute("DELETE FROM veiculos_moradores WHERE id=?", (id_registro,))
            conn.commit()
            conn.close()
            self.carregar_dados()

    def exportar_relatorio(self):
        if self.nivel == "OPERADOR":
            messagebox.showerror("Acesso Negado", "Operadores não têm permissão para exportar dados.")
            return

        try:
            import pandas as pd
            from datetime import datetime
            
            pasta_export = PASTA_BASE / "Arquivos_Excel"
            pasta_export.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(str(ARQUIVO_DB))
            df = pd.read_sql_query("SELECT id, apartamento, bloco, marca, modelo, tipo, cor, placa, vaga_garagem, tamanho_vaga, morador FROM veiculos_moradores ORDER BY bloco, apartamento", conn)
            conn.close()
            
            if df.empty:
                messagebox.showinfo("Aviso", "Não há dados para exportar.")
                return
                
            df.columns = ["ID", "Apto", "Bloco", "Marca", "Modelo", "Tipo", "Cor", "Placa", "Vaga Garagem", "Tamanho Vaga", "Condutor"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = pasta_export / f"Relatorio_Veiculos_Condutores_{timestamp}.xlsx"
            
            df.to_excel(str(caminho), index=False)
            
            if messagebox.askyesno("Sucesso", "Planilha exportada!\nDeseja abrir agora?"):
                os.startfile(str(caminho))
                
        except Exception as e:
            messagebox.showerror("Erro", f"Falha na exportação: {e}")

    def limpar_campos(self):
        for entry in [self.ent_condutor, self.ent_apt, self.ent_marca, self.ent_modelo, self.ent_cor, self.ent_placa, self.ent_vaga]:
            entry.delete(0, 'end')

    def carregar_dados(self):
        for i in self.tabela.get_children(): 
            self.tabela.delete(i)
        
        conn = sqlite3.connect(str(ARQUIVO_DB))
        cursor = conn.execute("SELECT id, apartamento, bloco, marca, modelo, tipo, cor, placa, vaga_garagem, tamanho_vaga, morador FROM veiculos_moradores ORDER BY bloco, apartamento") 
        
        for r in cursor.fetchall(): 
            linha = list(r)
            for i in range(len(linha)): 
                if linha[i] == "" or linha[i] is None: 
                    linha[i] = "-"
            self.tabela.insert("", "end", values=linha)
            
        conn.close()