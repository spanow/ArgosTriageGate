"""Évaluation des modèles de décision sur un GPU Modal.

Depuis la racine du dépôt :
    uv run modal run cloud/modal_app.py --model wazn                    (principal + robustesse + large-K + ablation)
    uv run modal run cloud/modal_app.py --model strands                 (principal + robustesse ; large-K impossible : 24 options max)
    uv run modal run cloud/modal_app.py --model wazn --tasks main       (une seule tâche : main, robustness, largek, ablation)

Dans le conteneur (GPU L4), le serveur du modèle démarre sur localhost et les scripts d'évaluation du dépôt
l'interrogent comme en local. Les résultats sont écrits dans results/. Les poids sont gardés dans le volume
`argos-hf-cache`. Les deux images partagent les mêmes versions de torch, transformers et flash-linear-attention.
"""

import subprocess
import time
from pathlib import Path

import modal

LOCAL_ROOT = Path(__file__).resolve().parent.parent
REMOTE_ROOT = "/root/argos"
GPU = "L4"  # 24 Go, bfloat16 natif

app = modal.App("argos-eval")
hf_cache = modal.Volume.from_name("argos-hf-cache", create_if_missing=True)

COMMON = ("torch==2.14.1", "transformers==5.18.0", "flash-linear-attention>=0.5", "httpx", "pyyaml")


def project_image(*packages: str) -> modal.Image:
    """Image Linux + paquets du modèle + notre code (triage/, scripts/, data/), lancé depuis REMOTE_ROOT."""
    return (
        modal.Image.debian_slim(python_version="3.12")
        .uv_pip_install(*COMMON, *packages)
        .env({"HF_HOME": "/hf-cache", "HF_HUB_DISABLE_TELEMETRY": "1", "PYTHONPATH": REMOTE_ROOT,
              "PYTHONIOENCODING": "utf-8"})
        .add_local_dir(LOCAL_ROOT / "triage", f"{REMOTE_ROOT}/triage")
        .add_local_dir(LOCAL_ROOT / "scripts", f"{REMOTE_ROOT}/scripts")
        .add_local_dir(LOCAL_ROOT / "data", f"{REMOTE_ROOT}/data")
    )


wazn_image = project_image("wazn-experimental[server,cuda]==0.1.0a1")
strands_image = project_image("strands-decider==0.1.0")

SERVERS = {
    "wazn": (["wazn-experimental", "serve", "--model", "numidlabs/wazn-2b-v0.1", "--host", "127.0.0.1",
              "--port", "8000"], "http://127.0.0.1:8000/health"),
    "strands": (["strands-decider", "serve", "StrandsAgents/strands-decider-2B-hobson-v21", "--host", "127.0.0.1",
                 "--port", "8001", "--device", "cuda"], "http://127.0.0.1:8001/health"),
}

# tâche → commande (lancée depuis REMOTE_ROOT) ; {hw} = description du GPU
TASKS = {
    "main": ["python", "-m", "triage.eval.run", "--adapter", "{model}", "--hardware", "{hw}"],
    "robustness": ["python", "-m", "triage.eval.run", "--adapter", "{model}", "--dataset", "robustness",
                   "--hardware", "{hw}"],
    "largek": ["python", "scripts/run_large_k.py"],
    "ablation": ["python", "scripts/latency_ablation.py"],
}
DEFAULT_TASKS = {"wazn": "main,robustness,largek,ablation", "strands": "main,robustness"}


def gpu_description() -> str:
    name = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout.strip()
    return f"Modal, {name}, CUDA, torch 2.14.1, flash-linear-attention installed"


def run_tasks(model: str, tasks: list[str]) -> dict[str, str]:
    """Démarre le serveur du modèle, lance les tâches, renvoie {nom de fichier: contenu} des résultats."""
    import httpx

    command, health = SERVERS[model]
    server = subprocess.Popen(command)
    try:
        deadline = time.time() + 1800  # 1er lancement : téléchargement des poids dans le volume
        while True:
            try:
                if httpx.get(health, timeout=5).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if server.poll() is not None or time.time() > deadline:
                raise RuntimeError(f"le serveur {model} n'a pas démarré")
            time.sleep(5)
        hf_cache.commit()  # poids gardés pour les prochaines fois

        hardware = gpu_description()
        print(f"Serveur {model} prêt sur {hardware}", flush=True)
        for task in tasks:
            subprocess.run([part.format(model=model, hw=hardware) for part in TASKS[task]], cwd=REMOTE_ROOT,
                           check=True)
    finally:
        server.terminate()

    results = Path(REMOTE_ROOT) / "results"
    return {f.name: f.read_text(encoding="utf-8") for f in results.glob("*.json")}


@app.function(image=wazn_image, gpu=GPU, volumes={"/hf-cache": hf_cache}, timeout=3600)
def evaluate_wazn(tasks: list[str]) -> dict[str, str]:
    return run_tasks("wazn", tasks)


@app.function(image=strands_image, gpu=GPU, volumes={"/hf-cache": hf_cache}, timeout=3600)
def evaluate_strands(tasks: list[str]) -> dict[str, str]:
    return run_tasks("strands", tasks)


@app.local_entrypoint()
def main(model: str = "wazn", tasks: str = ""):
    if model not in DEFAULT_TASKS:
        raise SystemExit("--model wazn ou --model strands")
    selected = (tasks or DEFAULT_TASKS[model]).split(",")
    if model == "strands" and "largek" in selected:
        raise SystemExit("Strands accepte 24 options au plus : la scène large-K (36 équipes) ne s'applique pas.")
    function = evaluate_wazn if model == "wazn" else evaluate_strands
    files = function.remote(selected)
    out = LOCAL_ROOT / "results"
    out.mkdir(exist_ok=True)
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")
        print(f"→ results/{name}")
