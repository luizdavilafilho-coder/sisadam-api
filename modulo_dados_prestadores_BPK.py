import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
import pathlib
import os
from datetime import datetime

# Configuração de Caminhos Unificados do SISADAM
PASTA_BASE = pathlib.Path.home() / "Documents" / "SISADAM"
PASTA_BANCO = PASTA_BASE / "Arquivos_Banco"
ARQUIVO_DB = PASTA_BANCO / "prestadores.db"

class BancoPrestadores(ctk.CTkFrame):
    def __init__(self, master, nivel="OPERADOR", usuario="USUÁRIO", **kwargs):
        super().__init__(master, **kwargs)
        self.cor_destaque = "#F57C00"
        self.nivel = nivel
        self.usuario_logado = usuario # Agora self.usuario_logado recebe o nome correto
        PASTA_BANCO.mkdir(parents=True, exist_ok=True)
        
        self.criar_banco()
        self.montar_interface()
        self.aplicar_permissoes()
        self.carregar_dados()

    def criar_banco(self):
        conn = sqlite3.connect(str(ARQUIVO_DB))
        conn.execute('''CREATE TABLE IF NOT EXISTS prestadores (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            empresa TEXT, 
                            prestador TEXT, 
                            documento TEXT,
                            local TEXT,
                            bloco TEXT,
                            apartamento TEXT,
                            autorizado_por TEXT,
                            hora_entrada TEXT,
                            hora_saida TEXT)''')
        conn.commit()
        conn.close()

    def fechar_ciclo_diario(self):
        """Exportação automática dos prestadores para o Cofre à meia-noite"""
        try:
            import pandas as pd
            import sqlite3
            import pathlib
            from datetime import datetime, timedelta
            
            # Caminhos específicos para Prestadores (Padrão SISADAM)
            p_base = pathlib.Path.home() / "Documents" / "SISADAM"
            p_banco = p_base / "Arquivos_Banco" / "prestadores.db"
            p_cofre = p_base / "Cofre_Backup" / "Prestadores"
            p_cofre.mkdir(parents=True, exist_ok=True)
            
            # Data de referência (ontem)
            ontem = (datetime.now() - timedelta(days=1)).strftime('%d-%m-%Y')
            caminho_excel = p_cofre / f"Relatorio_Prestadores_{ontem}.xlsx"
            
            # Conecta e gera o backup
            conn = sqlite3.connect(str(p_banco))
            df = pd.read_sql_query("SELECT * FROM prestadores", conn)
            df.to_excel(caminho_excel, index=False)
            conn.close()
            
            # Reseta a interface para o novo dia
            self.carregar_dados()
            self.reset_total()
            
            print(f"Backup de Prestadores concluído: {caminho_excel}")
        except Exception as e:
            print(f"Erro no backup automático de prestadores: {e}")

    def montar_interface(self):
        self.label_titulo = ctk.CTkLabel(self, text=f"Controle de Prestadores de Serviços [{self.nivel}]", font=("Roboto Mono", 24, "bold"), text_color=self.cor_destaque)
        self.label_titulo.pack(pady=15)

        # --- QUADRO DE FORMULÁRIO ---
        self.frame_form = ctk.CTkFrame(self, fg_color="#121212", corner_radius=12, border_width=1, border_color="#333333")
        self.frame_form.pack(pady=10, padx=20, fill="x")

        # LINHA 1
        self.ent_empresa = ctk.CTkEntry(self.frame_form, placeholder_text="EMPRESA PRESTADORA", width=250)
        self.ent_empresa.grid(row=0, column=0, padx=10, pady=10)

        self.ent_prestador = ctk.CTkEntry(self.frame_form, placeholder_text="NOME DO PRESTADOR", width=280)
        self.ent_prestador.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.ent_doc = ctk.CTkEntry(self.frame_form, placeholder_text="RG / CPF", width=150)
        self.ent_doc.grid(row=0, column=2, padx=10, pady=10)

        # LINHA 2
        self.ent_local = ctk.CTkComboBox(self.frame_form, values=["APARTAMENTO", "CONDOMÍNIO"], width=150)
        self.ent_local.set("LOCAL")
        self.ent_local.grid(row=1, column=0, padx=10, pady=(0, 10))

        self.frame_bloco_apto = ctk.CTkFrame(self.frame_form, fg_color="transparent")
        self.frame_bloco_apto.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="w")

        self.ent_bloco = ctk.CTkComboBox(self.frame_bloco_apto, values=["BLOCO A", "BLOCO B"], width=100)
        self.ent_bloco.set("BLOCO")
        self.ent_bloco.pack(side="left", padx=(0, 10))

        self.ent_apt = ctk.CTkEntry(self.frame_bloco_apto, placeholder_text="APTO", width=80)
        self.ent_apt.pack(side="left")

        self.ent_autorizado = ctk.CTkEntry(self.frame_form, placeholder_text="AUTORIZADO POR", width=250)
        self.ent_autorizado.grid(row=1, column=2, padx=10, pady=(0, 10))

        # --- BARRA DE AÇÕES ---
        self.frame_acoes = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_acoes.pack(pady=10, padx=20, fill="x")

        self.btn_novo = ctk.CTkButton(self.frame_acoes, text="+ NOVO REGISTRO", fg_color="#2E7D32", hover_color="#1B5E20", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.reset_total, width=150)
        self.btn_novo.pack(side="left", padx=5)

        self.btn_salvar = ctk.CTkButton(self.frame_acoes, text="SALVAR / ENTRADA", fg_color=self.cor_destaque, text_color="black", font=("Roboto Mono", 12, "bold"), command=self.salvar_registro, width=150)
        self.btn_salvar.pack(side="left", padx=5)

        self.btn_saida = ctk.CTkButton(self.frame_acoes, text="REGISTRAR SAÍDA", fg_color="#2E7D32", hover_color="#1B5E20", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.registrar_saida, width=150)
        self.btn_saida.pack(side="left", padx=5)

        self.btn_editar = ctk.CTkButton(self.frame_acoes, text="EDITAR REGISTRO", fg_color="#1E88E5", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.carregar_edicao, width=150)
        self.btn_editar.pack(side="left", padx=5)

        self.btn_deletar = ctk.CTkButton(self.frame_acoes, text="DELETAR", fg_color="#D32F2F", hover_color="#B71C1C", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.deletar_registro, width=100)
        self.btn_deletar.pack(side="right", padx=5)

        self.btn_exportar = ctk.CTkButton(self.frame_acoes, text="📊 EXPORTAR HOJE", fg_color="#1D6F42", hover_color="#144C2D", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.exportar_relatorio, width=180)
        self.btn_exportar.pack(side="right", padx=5)

        self.btn_limpar = ctk.CTkButton(self.frame_acoes, text="LIMPAR", fg_color="#757575", text_color="white", font=("Roboto Mono", 12, "bold"), command=self.limpar_campos, width=100)
        self.btn_limpar.pack(side="right", padx=5)

        # --- TABELA ---
        self.frame_tabela = ctk.CTkFrame(self)
        self.frame_tabela.pack(pady=10, padx=20, fill="both", expand=True)

        colunas = ("ID", "Empresa", "Prestador", "Doc.", "Local", "Bloco", "Apto", "Autorizado Por", "Entrada", "Saída")
        self.tabela = ttk.Treeview(self.frame_tabela, columns=colunas, show="headings")
        
        for col in colunas:
            self.tabela.heading(col, text=col)
            if col in ["Empresa", "Prestador", "Autorizado Por"]: largura = 130
            elif col in ["Entrada", "Saída"]: largura = 120
            elif col in ["ID", "Apto"]: largura = 50
            else: largura = 80
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
        self.limpar_campos()
        self.ent_local.set("LOCAL")
        self.ent_bloco.set("BLOCO")
        self.id_em_edicao = None
        self.btn_salvar.configure(text="SALVAR / ENTRADA")

    def salvar_registro(self):
        dados = (
            self.ent_empresa.get().strip().upper(), 
            self.ent_prestador.get().strip().upper(),
            self.ent_doc.get().strip().upper(), 
            self.ent_local.get(),
            self.ent_bloco.get() if self.ent_bloco.get() != "BLOCO" else "",
            self.ent_apt.get().strip().upper(),
            self.ent_autorizado.get().strip().upper()
        )

        if not dados[1] or not dados[6]:
            messagebox.showwarning("Aviso", "Nome do Prestador e Autorizado Por são obrigatórios.")
            return

        conn = sqlite3.connect(str(ARQUIVO_DB))
        if self.id_em_edicao:
            if self.nivel != "MASTER":
                messagebox.showerror("Erro", "Ação restrita ao nível MASTER.")
                conn.close()
                return
            conn.execute('''UPDATE prestadores SET empresa=?, prestador=?, documento=?, local=?, bloco=?, apartamento=?, autorizado_por=? WHERE id=?''', 
                         (*dados, self.id_em_edicao))
            messagebox.showinfo("Sucesso", "Registro atualizado.")
        else:
            hora_entrada = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.execute('''INSERT INTO prestadores (empresa, prestador, documento, local, bloco, apartamento, autorizado_por, hora_entrada, hora_saida) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (*dados, hora_entrada, "---"))
            messagebox.showinfo("Sucesso", f"Entrada registrada às {hora_entrada}")
            
        conn.commit()
        conn.close()
        self.reset_total()
        self.carregar_dados()

    def registrar_saida(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um registro.")
            return
        valores = self.tabela.item(selecionado[0])['values']
        if valores[9] != "---":
            messagebox.showinfo("Aviso", "Saída já registrada.")
            return

        hora_saida = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = sqlite3.connect(str(ARQUIVO_DB))
        conn.execute("UPDATE prestadores SET hora_saida=? WHERE id=?", (hora_saida, valores[0]))
        conn.commit()
        conn.close()
        messagebox.showinfo("Saída", f"Saída registrada às {hora_saida}")
        self.carregar_dados()

    def carregar_edicao(self):
        if self.nivel != "MASTER":
            messagebox.showerror("Erro", "Ação restrita ao nível MASTER.")
            return
        selecionado = self.tabela.selection()
        if not selecionado: return
        
        valores = self.tabela.item(selecionado[0])['values']
        self.id_em_edicao = valores[0]
        self.limpar_campos()
        self.ent_empresa.insert(0, valores[1])
        self.ent_prestador.insert(0, valores[2])
        self.ent_doc.insert(0, str(valores[3]))
        self.ent_local.set(valores[4])
        self.ent_bloco.set(valores[5] if valores[5] != "-" else "BLOCO")
        self.ent_apt.insert(0, str(valores[6]) if valores[6] != "-" else "")
        self.ent_autorizado.insert(0, valores[7])
        self.btn_salvar.configure(text="ATUALIZAR DADOS")

    def deletar_registro(self):
        if self.nivel != "MASTER":
            messagebox.showerror("Erro", "Ação restrita ao nível MASTER.")
            return
        selecionado = self.tabela.selection()
        if not selecionado: return
        if messagebox.askyesno("Confirmação", "Excluir permanentemente este registro?"):
            conn = sqlite3.connect(str(ARQUIVO_DB))
            conn.execute("DELETE FROM prestadores WHERE id=?", (self.tabela.item(selecionado[0])['values'][0],))
            conn.commit()
            conn.close()
            self.carregar_dados()

    def exportar_relatorio(self):
        if self.nivel == "OPERADOR": return
        try:
            import pandas as pd
            pasta_export = PASTA_BASE / "Arquivos_Excel"
            pasta_export.mkdir(parents=True, exist_ok=True)
            data_hoje = datetime.now().strftime("%d/%m/%Y")
            
            conn = sqlite3.connect(str(ARQUIVO_DB))
            df = pd.read_sql_query("SELECT * FROM prestadores WHERE hora_entrada LIKE ? ORDER BY id DESC", conn, params=(f"{data_hoje}%",))
            conn.close()

            if df.empty:
                messagebox.showinfo("Aviso", "Sem entradas hoje para exportar.")
                return

            df.columns = ["ID", "Empresa", "Prestador", "Doc.", "Local", "Bloco", "Apto", "Autorizado Por", "Entrada", "Saída"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = pasta_export / f"Relatorio_Prestadores_{timestamp}.xlsx"
            df.to_excel(str(caminho), index=False)
            if messagebox.askyesno("Sucesso", "Deseja abrir a planilha?"):
                os.startfile(str(caminho))
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar: {e}")

    def limpar_campos(self):
        for entry in [self.ent_empresa, self.ent_prestador, self.ent_doc, self.ent_apt, self.ent_autorizado]:
            entry.delete(0, 'end')

    def carregar_dados(self):
        for i in self.tabela.get_children(): self.tabela.delete(i)
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        conn = sqlite3.connect(str(ARQUIVO_DB))
        cursor = conn.execute("SELECT * FROM prestadores WHERE hora_entrada LIKE ? ORDER BY id DESC", (f"{data_hoje}%",))
        for r in cursor.fetchall():
            linha = list(r)
            for i in range(len(linha)):
                if not linha[i] or linha[i] == "": linha[i] = "-"
            self.tabela.insert("", "end", values=linha)
        conn.close()