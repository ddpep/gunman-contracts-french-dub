import os

ALIGN = 4096


def inject_payloads(assets_path, resource_path, out_assets, out_resource, payloads,
                     lengths=None):

    import UnityPy
    from UnityPy.classes import StreamedResource

    blob = bytearray(open(resource_path, "rb").read())
    env = UnityPy.load(assets_path)
    n = 0
    for obj in env.objects:
        if obj.type.name != "AudioClip":
            continue
        data = obj.read()
        name = getattr(data, "m_Name", "")
        payload = payloads.get(name)
        if payload is None:
            continue
        if len(blob) % ALIGN:
            blob += b"\x00" * (ALIGN - len(blob) % ALIGN)
        offset = len(blob)
        blob += payload
        src_name = (data.m_Resource.m_Source if data.m_Resource and data.m_Resource.m_Source
                    else os.path.basename(resource_path))
        data.m_Resource = StreamedResource(m_Offset=offset, m_Size=len(payload),
                                          m_Source=src_name)
        if lengths is not None and name in lengths:
            data.m_Length = lengths[name]
        data.save()
        n += 1
    assets_file = next(iter(env.files.values())).save(packer="none")
    open(out_assets, "wb").write(assets_file)
    open(out_resource, "wb").write(bytes(blob))
    return n, len(blob)


def load_payloads(vo_repo, manifest_entries, by_asset=None):
    out = {}
    for e in manifest_entries:
        if by_asset is not None and e["asset"] != by_asset:
            continue
        p = os.path.join(vo_repo, e["payload"])
        out[e["key"]] = open(p, "rb").read()
    return out
