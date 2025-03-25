from lxml import html
import re

def parse_html_content(html_content):
    """
    Processa cada tabela com classe "jrPage" para extrair turmas e alunos.
    
    Para cada tabela:
      1. Procura o primeiro <tr> que contenha "Turma:" (ignorando linhas com "Total de Matrículas")
         e extrai o nome da turma considerando tudo que vem depois de "Turma:" até o primeiro ")".
      2. Percorre as linhas seguintes da mesma tabela para localizar a linha de cabeçalho que contenha "Código" e "Nome".
      3. Determina o índice da coluna "Nome" nessa linha de cabeçalho.
      4. A partir da linha imediatamente após o cabeçalho, extrai os nomes dos alunos (usando a célula da coluna "Nome")
         até encontrar uma linha que contenha "Total de Matrículas" ou "Turma:".
      5. Se a turma continuar em outra tabela (sem um novo marcador "Turma:"), continua a extração de alunos.
         
    Retorna:
      dict: Chave = nome da turma, Valor = lista de nomes de alunos.
    """
    tree = html.fromstring(html_content)
    classes = {}
    current_turma = None  # Para armazenar a última turma processada
    
    # Processa cada tabela principal (geralmente com classe "jrPage")
    tables = tree.xpath("//table[contains(@class, 'jrPage')]")
    
    for table in tables:
        rows = table.xpath(".//tr")
        turma_row = None
        
        # Procura a primeira linha que contenha "Turma:" (mas não "Total de Matrículas")
        for row in rows:
            row_text = row.text_content().strip()
            if "Turma:" in row_text and "Total de Matrículas" not in row_text:
                turma_row = row
                break
        
        if turma_row:
            # Extrai o nome da turma: tudo após "Turma:" até o primeiro ")".
            turma_text = turma_row.text_content().strip()
            match = re.search(r'Turma:\s*(.+?\))', turma_text)
            if match:
                current_turma = match.group(1).strip()
                if current_turma not in classes:
                    classes[current_turma] = []
        
        if not current_turma:
            continue  # Se nenhuma turma foi definida, pula a tabela
        
        # Procura a linha de cabeçalho que contenha "Código" e "Nome"
        header_row = None
        header_index = None
        for idx, row in enumerate(rows):
            text = row.text_content().strip()
            if "Código" in text and "Nome" in text:
                header_row = row
                header_index = idx
                break
        if header_row is None or header_index is None:
            continue
        
        # Determina o índice da coluna "Nome" na linha de cabeçalho.
        header_cells = header_row.xpath(".//th")
        if not header_cells:
            header_cells = header_row.xpath(".//td")
        nome_index = None
        for i, cell in enumerate(header_cells):
            if "Nome" in cell.text_content():
                nome_index = i
                break
        if nome_index is None:
            continue
        
        # A partir da linha imediatamente após o cabeçalho, extrai os nomes
        students = []
        for row in rows[header_index + 1:]:
            row_text = row.text_content().strip()
            if "Total de Matrículas" in row_text or "Turma:" in row_text:
                break
            cells = row.xpath(".//td")
            if len(cells) > nome_index:
                student_name = cells[nome_index].text_content().strip()
                if student_name and re.search(r'[A-Za-zÀ-ÖØ-öø-ÿ]', student_name):
                    students.append(student_name)
        
        classes[current_turma].extend(students)  # Adiciona os alunos à turma existente
    
    return classes

# Exemplo de uso:
if __name__ == '__main__':
    file_path = "RelatorioEmitidoPeloEducarWEB (1).html"
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    turmas = parse_html_content(html_content)
    for turma, alunos in turmas.items():
        print(f"Turma: {turma} - {len(alunos)} alunos")
        for aluno in alunos:
            print("   ", aluno)