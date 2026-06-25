"""CLI: coletar | resumir | consenso | ciclo | api | scheduler."""
from __future__ import annotations

import argparse
import logging

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cartógrafo — pipeline de cartas de gestores")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("coletar", help="coleta a carta mais recente das fontes implementadas")
    sub.add_parser("resumir", help="gera resumos dos documentos pendentes (requer IA acoplada)")
    sub.add_parser("consenso", help="gera o relatório de consenso/divergência")
    sub.add_parser("ciclo", help="executa coleta + resumo + consenso")
    p_api = sub.add_parser("api", help="sobe a API + painel web")
    p_api.add_argument("--host", default="127.0.0.1")
    p_api.add_argument("--port", type=int, default=8000)
    sub.add_parser("scheduler", help="inicia o agendador (APScheduler)")

    args = parser.parse_args()

    if args.cmd == "coletar":
        from .pipeline import executar_coleta
        executar_coleta()
    elif args.cmd == "resumir":
        from .pipeline import executar_resumos
        executar_resumos()
    elif args.cmd == "consenso":
        from .pipeline import executar_consenso
        executar_consenso()
    elif args.cmd == "ciclo":
        from .pipeline import executar_ciclo_completo
        executar_ciclo_completo()
    elif args.cmd == "api":
        import uvicorn
        uvicorn.run("cartografo.api.app:app", host=args.host, port=args.port, reload=False)
    elif args.cmd == "scheduler":
        from .scheduler import iniciar_agendador
        iniciar_agendador()


if __name__ == "__main__":
    main()
