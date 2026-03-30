# CocoWizard Cue Engine

Aplicacao em Python para controle de apresentacoes teatrais/roboticas baseada em `cues` (gatilhos de execucao), com foco em sincronizacao confiavel de palco.

O sistema atual executa um roteiro linear em fila FIFO e suporta:

- reproducao de video
- delays curtos controlados
- espera manual do operador
- envio mockado de comandos para robos

## Visao Geral

Em vez de depender apenas de timers fixos, o roteiro e modelado como uma sequencia ordenada de `cues`.

Cada cue representa uma acao discreta do show, por exemplo:

```python
{"type": "video", "file": "midia/video1.mp4"}
{"type": "wait", "duration": 2}
{"type": "wait_manual"}
{"type": "robot", "command": "MOVE_FORWARD"}
```

A engine consome esses cues em ordem e executa a acao correta para cada tipo.

Esse modelo e mais robusto para teatro porque permite sincronizar a execucao com atores humanos, variacoes de cena e intervencao do operador.

## Estado Atual Do Projeto

Hoje o projeto esta focado em uma `cue engine` linear.

Fluxo implementado:

1. tocar `midia/video1.mp4`
2. esperar `2` segundos
3. esperar liberacao manual do operador
4. tocar `midia/video2.mp4`
5. enviar comando `MOVE_FORWARD` para o robo
6. finalizar

Videos detectados no projeto:

- `midia/video1.mp4`
- `midia/video2.mp4`

## Arquitetura

### `main.py`

Ponto de entrada da aplicacao.

Responsabilidades:

- montar o roteiro
- instanciar os controladores
- iniciar a execucao da cue engine
- tratar interrupcao do operador

### `cue_engine.py`

Core da execucao do roteiro.

Responsabilidades:

- converter a lista de dicionarios em cues tipados
- armazenar os cues em uma fila FIFO
- consumir e executar os cues em ordem
- delegar a execucao para os handlers apropriados

Tipos de cue suportados:

- `video`
- `wait`
- `wait_manual`
- `robot`

### `media_controller.py`

Camada de reproducao de video.

Responsabilidades:

- validar se o arquivo existe
- abrir o video com OpenCV
- reproduzir quadro a quadro
- encerrar ao fim do video
- permitir interrupcao com `q`

### `robot_comm.py`

Mock da comunicacao com robos.

Responsabilidades:

- receber um comando textual
- registrar no terminal a intencao de envio

No futuro, esse modulo pode ser substituido por serial, Wi-Fi, Bluetooth ou MQTT sem alterar a cue engine.

## Estrutura De Pastas

```text
cocoWizard/
├── main.py
├── cue_engine.py
├── media_controller.py
├── robot_comm.py
├── requirements.txt
├── .gitignore
└── midia/
    ├── video1.mp4
    └── video2.mp4
```

## Como Funciona Na Pratica

1. O operador executa a aplicacao.
2. O `main.py` monta o roteiro em forma de lista.
3. A `CueEngine` transforma essa lista em uma fila FIFO.
4. Cada cue e executado em sequencia.
5. Quando a engine encontra um `wait_manual`, ela pausa.
6. O operador libera a continuidade apertando `ENTER` ou `n`.
7. O sistema segue ate o ultimo cue.

## Instalacao

### Requisitos

- Python 3.11+
- OpenCV para reproducao de video

### Instalar dependencias

Se estiver usando um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Observacao:

- `opencv-python` e usado no estado atual da cue engine
- `mediapipe` esta no `requirements.txt` por conta da fase anterior do projeto e nao e necessario para o fluxo atual de cues

## Execucao

No diretorio do projeto:

```bash
python3 main.py
```

Se estiver usando ambiente virtual:

```bash
source .venv/bin/activate
python main.py
```

## Controles Do Operador

### Durante `wait_manual`

- `ENTER` -> continua para o proximo cue
- `n` -> continua para o proximo cue
- `q` -> aborta a execucao

### Durante reproducao de video

- `q` -> interrompe a execucao

## Exemplo De Roteiro

O roteiro atual e definido em `build_show_script()` dentro de `main.py`:

```python
def build_show_script() -> list[dict[str, object]]:
    return [
        {"type": "video", "file": "midia/video1.mp4"},
        {"type": "wait", "duration": 2},
        {"type": "wait_manual"},
        {"type": "video", "file": "midia/video2.mp4"},
        {"type": "robot", "command": "MOVE_FORWARD"},
    ]
```

## Formato Dos Cues

### Cue de video

```python
{"type": "video", "file": "midia/video1.mp4"}
```

Executa um video e bloqueia ate o fim da reproducao.

### Cue de espera curta

```python
{"type": "wait", "duration": 2}
```

Faz uma pausa controlada em segundos. Deve ser usado apenas para pequenas sincronizacoes tecnicas.

### Cue de espera manual

```python
{"type": "wait_manual"}
```

Para a execucao ate intervencao do operador.

### Cue de robo

```python
{"type": "robot", "command": "MOVE_FORWARD"}
```

Envia um comando mockado para o modulo de comunicacao do robo.

## Como Adicionar Mais Videos

1. Coloque o novo arquivo dentro de `midia/`
2. Adicione um novo cue do tipo `video` no roteiro

Exemplo:

```python
{"type": "video", "file": "midia/video3.mp4"}
```

## Como Transformar Isso Em Sistema De Cenas

O proximo passo natural e agrupar cues por cenas.

Exemplo conceitual:

```python
SCENES = {
    "ABERTURA": [
        {"type": "video", "file": "midia/video1.mp4"},
        {"type": "wait_manual"},
    ],
    "CLIMAX": [
        {"type": "video", "file": "midia/video2.mp4"},
        {"type": "robot", "command": "MOVE_FORWARD"},
    ],
}
```

Depois disso, um `scene_runner` pode carregar a lista de cues da cena atual e executar bloco por bloco.

Beneficios:

- melhor organizacao do roteiro
- reutilizacao de blocos
- transicoes mais claras
- base pronta para branching futuro

## Como Integrar Visao Computacional Depois

A integracao futura com visao computacional deve seguir esta logica:

1. a camera detecta um gesto, objeto ou evento visual
2. isso vira um gatilho do sistema
3. o gatilho libera uma cena ou injeta um cue
4. a cue engine continua sendo o executor do roteiro

Importante:

- visao computacional nao deve tocar video ou mover robo diretamente
- ela deve apenas gerar eventos/gatilhos
- a execucao concreta continua centralizada na cue engine

Isso preserva a separacao entre percepcao e controle cenario.

## Motivacao Tecnica

Uma cue engine e preferivel a um sistema puramente temporal porque:

- palco real tem variacao humana
- atores nao seguem milissegundos fixos
- robos podem precisar de confirmacao externa
- operacao manual precisa existir como plano seguro
- sincronizacao precisa ser previsivel e auditavel

## Pontos Fortes Da Implementacao Atual

- arquitetura pequena e clara
- fila FIFO simples e confiavel
- sem dependencias pesadas de framework
- facil de testar
- facil de expandir
- controle manual pronto para uso em apresentacao

## Limitacoes Atuais

- cues ainda sao definidos diretamente em `main.py`
- nao ha persistencia de estado
- nao ha log estruturado
- o modulo de robo ainda e mockado
- videos sao reproduzidos em uma janela OpenCV simples

## Proximos Passos Recomendados

- mover o roteiro para JSON ou YAML
- agrupar cues em cenas
- adicionar logs de execucao por cue
- adicionar confirmacoes de sucesso dos robos
- suportar audio dedicado
- suportar gatilhos externos como visao computacional ou botao fisico

## Git E Publicacao

Foi adicionado um `.gitignore` para evitar subir arquivos locais como:

- `.venv/`
- `.runtime/`
- `__pycache__/`
- `.DS_Store`

Se esses arquivos ja tiverem entrado no commit, o `.gitignore` sozinho nao basta. Eles precisam ser removidos do indice do Git.

## Licenca

Uso interno / projeto em desenvolvimento.
