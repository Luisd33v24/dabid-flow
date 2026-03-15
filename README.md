#  Sistema de Gestão Financeira Desktop

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![Windows API](https://img.shields.io/badge/Windows_API-0078D6?style=for-the-badge&logo=windows&logoColor=white)

Este repositório contém uma aplicação desktop voltada para o controle de fluxo de caixa e análise de dados financeiros. Desenvolvido em Python, o projeto transcende a simples criação de interfaces gráficas, enfatizando conceitos técnicos como persistência segura de dados local, chamadas nativas à API do Sistema Operacional e algoritmos de redundância.

##  Arquitetura Interna e Integração com S.O.

O desenvolvimento deste software prioriza a compreensão profunda de interações de baixo nível e manipulação de arquivos:

* Ocultação de Diretórios e Variáveis de Ambiente: O armazenamento do banco de dados é gerido dinamicamente via variáveis de ambiente (%APPDATA% no Windows ou ~ no Linux). Em ambientes Windows, o sistema realiza chamadas diretas à API através da biblioteca ctypes (kernel32.SetFileAttributesW) para alterar os atributos binários do diretório, ocultando-o no sistema de arquivos.
* Redundância e Prevenção de Perda de Dados (DLP): Implementação de um algoritmo de backup rotativo em cascata (manipulação de I/O via shutil). O sistema mantém cópias versionadas do banco de dados em disco, mitigando severamente o risco de corrupção de dados decorrente de interrupções de escrita.
* Renderização Gráfica Nativamente Escalável (DPI Awareness): O software executa chamadas diretas à shcore.dll do Windows para habilitar o DPI Awareness em nível de processo. Isso garante que o pipeline de renderização ignore o escalonamento virtual do S.O., mantendo a fidelidade visual em displays de alta densidade de pixels.
* Validação de Integridade Binária: Durante o processo de inicialização, o software submete o arquivo do banco de dados a diretrizes internas do motor SQLite (PRAGMA integrity_check). Este procedimento certifica que o arquivo não apresenta anomalias estruturais antes de estabelecer a conexão com o banco.

##  Recursos da Aplicação

* Controle Lógico de Ativos: Segmentação estrutural em tempo real entre o fluxo de caixa operacional diário e o fundo de reserva (aportes e resgates).
* Visualização de Dados e Drill-down: Geração de relatórios visuais utilizando Matplotlib renderizado no canvas do Tkinter. Suporta navegação cronológica aprofundada nos níveis anual, mensal, diário e intradiário (hora/minuto).
* Motor de Busca Otimizado: Consultas SQL parametrizadas e projetadas para filtragem por substrings, formatações de data específicas e valores de ponto flutuante, incluindo tratamento para mitigação de erros de precisão decimal.

##  Estrutura Modular

O código-fonte foi refatorado e dividido visando alta coesão e baixo acoplamento:

* configuracoes.py: Gerenciamento de constantes e esquema de cores da aplicação.
* utilidades.py: Funções puras para sanitização de inputs, formatação de dados e handlers de UI.
* banco_dados.py: Motor de conexão SQLite, rotinas de I/O, backup e chamadas de sistema.
* main.py: Entry point da aplicação, orquestração de UI (Tkinter) e renderização gráfica.

##  Instruções de Implantação

1. Clone este repositório no seu ambiente local:
git clone https://github.com/Luisd33v24/sistema-de-caixa.git

2. Acesse o diretório do projeto:
cd sistema-de-caixa

3. Instale a dependência gráfica necessária:
pip install matplotlib

4. Inicie a aplicação:
python main.py

##  Autor

Luís Eduardo
Estudante do Curso Técnico em Informática (IFPB) | Focado em arquitetura de computadores, C/C++, Assembly, Engenharia Reversa e programação de baixo nível.

> "What I cannot create, I do not understand." — Richard Feynman

📧 Contato: luiseduardo38459@gmail.com
🐙 GitHub: https://github.com/Luisd33v24
