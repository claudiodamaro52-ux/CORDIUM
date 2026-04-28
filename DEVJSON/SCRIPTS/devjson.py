import json, csv, io, xml.etree.ElementTree as ET


def _count(data):
    if isinstance(data, dict):
        return f"{len(data)} chave(s)"
    if isinstance(data, list):
        return f"{len(data)} item(ns)"
    return "valor simples"


def run(op, text, text2="", param=""):
    result = ""
    msgs = []
    try:
        if op == "format":
            data = json.loads(text)
            result = json.dumps(data, indent=2, ensure_ascii=False)
            msgs = [f"Formatado. Raiz: {_count(data)}."]

        elif op == "minify":
            data = json.loads(text)
            result = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            msgs = [f"Minificado. {len(result)} caracteres."]

        elif op == "validate":
            try:
                data = json.loads(text)
                result = json.dumps(data, indent=2, ensure_ascii=False)
                msgs = ["JSON válido.", f"  Tipo raiz: {type(data).__name__}", f"  Elementos: {_count(data)}"]
            except json.JSONDecodeError as e:
                msgs = [f"JSON inválido - linha {e.lineno}, col {e.colno}: {e.msg}"]

        elif op == "to_csv":
            data = json.loads(text)
            if not isinstance(data, list):
                data = [data]
            buf = io.StringIO()
            if data and isinstance(data[0], dict):
                keys = list(data[0].keys())
                w = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
                w.writeheader()
                for row in data:
                    w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else (v if v is not None else "")) for k, v in row.items()})
            result = buf.getvalue()
            msgs = [f"Convertido para CSV. {len(data)} linha(s)."]

        elif op == "to_yaml":
            import yaml
            data = json.loads(text)
            result = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
            msgs = ["Convertido para YAML."]

        elif op == "to_xml":
            data = json.loads(text)
            root = ET.Element("root")
            _dict_to_xml(root, data)
            _indent_xml(root)
            result = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")
            msgs = ["Convertido para XML."]

        elif op == "from_csv":
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
            result = json.dumps(rows, indent=2, ensure_ascii=False)
            msgs = [f"CSV -> JSON. {len(rows)} linha(s)."]

        elif op == "from_yaml":
            import yaml
            data = yaml.safe_load(text)
            result = json.dumps(data, indent=2, ensure_ascii=False)
            msgs = ["YAML -> JSON."]

        elif op == "from_xml":
            root_el = ET.fromstring(text)
            data = _xml_to_dict(root_el)
            result = json.dumps(data, indent=2, ensure_ascii=False)
            msgs = ["XML -> JSON."]

        elif op == "jmespath":
            import jmespath as jmp
            data = json.loads(text)
            res = jmp.search(param, data)
            result = json.dumps(res, indent=2, ensure_ascii=False)
            msgs = [f"Query executada: {param}"]

        elif op == "diff":
            data1 = json.loads(text)
            data2 = json.loads(text2)
            diffs = []
            _diff(data1, data2, "", diffs)
            if diffs:
                result = "\n".join(diffs)
                msgs = [f"{len(diffs)} diferença(s) encontrada(s)."]
            else:
                result = "(Sem diferenças - JSONs idênticos)"
                msgs = ["JSONs idênticos."]

        elif op == "merge":
            data1 = json.loads(text)
            data2 = json.loads(text2)
            resultado = merge_deep(data1, data2)
            resultado = normalize_node(resultado)
            result = json.dumps(resultado, indent=2, ensure_ascii=False)
            msgs = [f"Mesclagem concluída. {len(resultado)} chave(s) no resultado."]

        elif op == "flatten":
            data = json.loads(text)
            flat = flatten_obj(data)
            flat = normalize_node(flat)
            result = json.dumps(flat, indent=2, ensure_ascii=False)
            msgs = [f"Flatten concluído. {len(flat)} chave(s) geradas."]

        elif op == "unflatten":
            data = json.loads(text)
            nested = unflatten_obj(data)
            nested = normalize_node(nested)
            result = json.dumps(nested, indent=2, ensure_ascii=False)
            msgs = [f"Unflatten concluído. {len(nested)} chave(s) de raiz."]

        elif op == "schema":
            data = json.loads(text)
            schema = make_schema(data)
            result = json.dumps(schema, indent=2, ensure_ascii=False)
            msgs = ["Schema gerado."]

        else:
            msgs = [f"Operação desconhecida: {op}"]

    except json.JSONDecodeError as e:
        msgs = [f"JSON inválido - linha {e.lineno}, col {e.colno}: {e.msg}"]
    except Exception as e:
        msgs = [f"Erro: {e}"]

    return result, msgs


def _dict_to_xml(parent, data):
    if isinstance(data, dict):
        for key, val in data.items():
            child = ET.SubElement(parent, str(key))
            _dict_to_xml(child, val)
    elif isinstance(data, list):
        for item in data:
            child = ET.SubElement(parent, "item")
            _dict_to_xml(child, item)
    else:
        parent.text = "" if data is None else str(data)


def _indent_xml(elem, level=0):
    pad = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = pad + "  "
        last = None
        for child in elem:
            _indent_xml(child, level + 1)
            last = child
        if last is not None and (not last.tail or not last.tail.strip()):
            last.tail = pad
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = pad


def _xml_to_dict(elem):
    d = {}
    for child in elem:
        val = _xml_to_dict(child)
        if child.tag in d:
            if not isinstance(d[child.tag], list):
                d[child.tag] = [d[child.tag]]
            d[child.tag].append(val)
        else:
            d[child.tag] = val
    return d if d else (elem.text or "")


def _diff(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            p = f"{path}.{k}" if path else k
            if k not in b:
                out.append(f"- Removido:   {p}  ->  {json.dumps(a[k], ensure_ascii=False)}")
            else:
                _diff(a[k], b[k], p, out)
        for k in b:
            if k not in a:
                p = f"{path}.{k}" if path else k
                out.append(f"+ Adicionado: {p}  ->  {json.dumps(b[k], ensure_ascii=False)}")
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(min(len(a), len(b))):
            _diff(a[i], b[i], f"{path}[{i}]", out)
        for i in range(len(b), len(a)):
            out.append(f"- Removido:   {path}[{i}]  ->  {json.dumps(a[i], ensure_ascii=False)}")
        for i in range(len(a), len(b)):
            out.append(f"+ Adicionado: {path}[{i}]  ->  {json.dumps(b[i], ensure_ascii=False)}")
    else:
        if a != b:
            out.append(f"~ Alterado: {path}\n    - {json.dumps(a, ensure_ascii=False)}\n    + {json.dumps(b, ensure_ascii=False)}")


def normalize_node(v):
    """Garante que chaves e valores sejam strings (padrao Cordium)."""
    if v is None:
        return ""
    if isinstance(v, list):
        return [normalize_node(i) for i in v]
    if isinstance(v, dict):
        return {str(k): normalize_node(val) for k, val in v.items()}
    return str(v)


def merge_deep(a, b):
    """Mescla dois dicts; b sobrescreve a em conflito. Arrays de b substituem os de a."""
    if isinstance(a, dict) and isinstance(b, dict):
        r = dict(a)
        for k, v in b.items():
            if k in r and isinstance(r[k], dict) and isinstance(v, dict):
                r[k] = merge_deep(r[k], v)
            else:
                r[k] = v
        return r
    return b


def flatten_obj(obj, prefix=""):
    """Achata JSON aninhado em chaves com ponto."""
    out = {}
    for k, v in obj.items():
        nova_chave = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten_obj(v, nova_chave))
        else:
            out[nova_chave] = "" if v is None else str(v)
    return out


def unflatten_obj(flat):
    """Reconstroi JSON aninhado a partir de chaves com ponto."""
    out = {}
    for chave, valor in flat.items():
        partes = chave.split(".")
        atual = out
        for parte in partes[:-1]:
            if parte not in atual or not isinstance(atual[parte], dict):
                atual[parte] = {}
            atual = atual[parte]
        atual[partes[-1]] = valor
    return out


def make_schema(v):
    """Gera JSON Schema simples (sem required, sem $schema)."""
    if isinstance(v, list):
        return {"type": "array", "items": make_schema(v[0]) if v else {}}
    if isinstance(v, dict):
        return {"type": "object", "properties": {k: make_schema(val) for k, val in v.items()}}
    return {"type": "string"}
