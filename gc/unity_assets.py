ALIGN = 4096


def clips(assets_path, wanted=None):
    import UnityPy
    found = {}
    for obj in UnityPy.load(assets_path).objects:
        if obj.type.name != "AudioClip":
            continue
        try:
            data = obj.read()
        except Exception:
            continue
        name = getattr(data, "m_Name", "")
        if wanted is not None and name not in wanted:
            continue
        found[name] = data
    return found


def resource_blob(resource_path):
    return open(resource_path, "rb").read()


def payload_at(blob, resource):
    if not resource:
        return None
    return bytes(blob[resource.m_Offset:resource.m_Offset + resource.m_Size])
