"""
Genera un PDF de prueba con texto real (sin dependencias externas) para ejercitar
el pipeline de IA de extremo a extremo.

Uso:
    python scripts/make_sample_pdf.py salida.pdf [--kind poliza|factura|carta]
                                      [--contract CONT-2026-042] [--nit 900123456-1]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TEMPLATES = {
    "poliza": [
        "SEGUROS DEL VALLE S.A. - POLIZA DE CUMPLIMIENTO No. {policy}",
        "Ramo: Arrendamiento de inmuebles comerciales",
        "Tomador / Afianzado: {client} - NIT {nit}",
        "Beneficiario: COLTEBIENES S.A. NIT 890.900.123-4",
        "Contrato amparado: {contract}",
        "Inmueble: {address}",
        "Vigencia desde: {start}   Vigencia hasta: {end}",
        "Fecha de expedicion: {issued}",
        "Valor asegurado: COP 48.000.000",
        "Este documento certifica la renovacion de la poliza de cumplimiento",
        "del contrato de arrendamiento indicado.",
    ],
    "factura": [
        "FACTURA DE VENTA No. FV-{policy}",
        "Emisor: {client} - NIT {nit}",
        "Cliente: COLTEBIENES S.A.",
        "Referencia: Contrato {contract} - {address}",
        "Fecha de emision: {issued}   Fecha de vencimiento: {end}",
        "Concepto: Mantenimiento preventivo de cubierta bodega",
        "Total: COP 3.450.000",
    ],
    "certificado": [
        "CAMARA DE COMERCIO DE MEDELLIN PARA ANTIOQUIA",
        "CERTIFICADO DE EXISTENCIA Y REPRESENTACION LEGAL",
        "Razon social: {client}",
        "NIT: {nit}",
        "Codigo de verificacion: {policy}",
        "Fecha de expedicion: {issued}",
        "Valido hasta: {end}",
        "Referencia contractual: {contract} - {address}",
        "El presente certificado se expide para acreditar la representacion legal",
        "ante COLTEBIENES S.A.",
    ],
    "carta": [
        "Medellin, {issued}",
        "Senores COLTEBIENES S.A.",
        "Asunto: Solicitud de autorizacion para adecuaciones - Contrato {contract}",
        "Respetados senores:",
        "En calidad de arrendatario ({client}, NIT {nit}) del inmueble ubicado en",
        "{address}, solicitamos autorizacion para instalar estanteria industrial.",
        "Agradecemos su pronta respuesta.",
        "Atentamente, Gerencia Administrativa",
    ],
}


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(lines: list[str]) -> bytes:
    content_parts = ["BT", "/F1 13 Tf", "50 740 Td", "16 TL"]
    for index, line in enumerate(lines):
        if index:
            content_parts.append("T*")
        content_parts.append(f"({_escape(line)}) Tj")
    content_parts.append("ET")
    content = "\n".join(content_parts).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    return bytes(out)


def sample_pdf(
    kind: str = "poliza",
    contract: str = "CONT-2026-042",
    nit: str = "900.123.456-1",
    client: str = "Logistica Andina S.A.S.",
    address: str = "Bodega 12, Parque Industrial Zona Franca, Rionegro",
    issued: str = "2026-09-15",
    start: str = "2026-10-01",
    end: str = "2027-09-30",
    policy: str = "88-2026-0451",
) -> bytes:
    lines = [
        line.format(
            contract=contract, nit=nit, client=client, address=address,
            issued=issued, start=start, end=end, policy=policy,
        )
        for line in TEMPLATES[kind]
    ]
    return build_pdf(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--kind", choices=sorted(TEMPLATES), default="poliza")
    parser.add_argument("--contract", default="CONT-2026-042")
    parser.add_argument("--nit", default="900.123.456-1")
    parser.add_argument("--client", default="Logistica Andina S.A.S.")
    args = parser.parse_args(argv)
    args.output.write_bytes(sample_pdf(args.kind, args.contract, args.nit, args.client))
    print(f"PDF generado: {args.output} ({args.output.stat().st_size} bytes)")


if __name__ == "__main__":
    sys.exit(main())
