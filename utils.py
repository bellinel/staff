def extract_link_and_tag(text):
    search_str = 'от <a href="'
    start = text.find(search_str)
    if start == -1:
        return None
    start += len(search_str)  # Перемещаем индекс после "от <a href="
    
    end = text.find('</a>', start)  # Находим конец тега </a>
    if end == -1:
        return None
    return text[start-9:end+4]  # Включаем сам тег <a> и </a>

# Пример:
text = 'Сообщение от <a href="tg://user?id=6264939461">Кикита</a>'
link = extract_link_and_tag(text)
print(link)  # <a href="tg://user?id=6264939461">Кикита</a>
