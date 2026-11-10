# PUBG AFK Helper

[简体中文](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/README.md) · [English](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.en.md) · [日本語](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.ja.md) · [Deutsch](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.de.md) · [Français](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.fr.md) · [Español](https://github.com/chenbinghan666/pubg-afk-helper/blob/main/docs/locales/README.es.md) · **Português**

Usa OpenCV para reconhecer telas de PUBG, exibir o estado da detecção e executar fluxos configuráveis no Windows. Inclui prévia apenas de detecção e testes de regressão offline.

Python · OpenCV · Windows

[![Windows tests](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml/badge.svg)](https://github.com/chenbinghan666/pubg-afk-helper/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB)

Ferramenta de processo automático PUBG baseada no reconhecimento de tela **OpenCV, entrada de simulação do Windows e detecção de alterações no minimapa**.
Identifique a interface de lobby e checkout, execute processos configuráveis de correspondência, salto, movimentação, retirada e escape e exiba a etapa atual por meio da janela de status superior.

## Função

- A interface **reconhece**: lobby, retorno ao lobby, confirmação de saída, liquidação de personagem e página de recompensa; confirmação de reconhecimento contínuo e limitar operações repetidas.
- Posicionamento relativo ****: dimensiona o modelo e as coordenadas de acordo com o tamanho da tela e oferece suporte à pesquisa alinhada às bordas para alguns layouts widescreen.
- Processo de jogo ****: salto no tempo após o corredor desaparecer, vire à direita uma vez, W + Shift esquerdo para continuar avançando, clique em F para pegar depois de olhar para baixo.
- **Parede anti-presa do minimapa**: Compare apenas o terreno do mapa no canto inferior direito e bloqueie a marca do caractere central; tente Shift+C primeiro, depois volte e mova para a esquerda e para a direita de acordo com os resultados da detecção.
- **Janela de status superior**: Exibe contagem regressiva, ações, motivos de pausa e indicadores de detecção de minimapa; a penetração do mouse não rouba o foco do jogo.
- **configurável e testável**: configuração JSON, ferramenta de gravação de modelo, teste de regressão offline, Windows CI.

O programa funciona por meio de capturas de tela e entradas normais do sistema operacional, não lê a memória do jogo e não injeta processos do jogo.
O projeto ainda está em fase inicial; horários fixos e alterações no minimapa são aproximados e não podem confirmar a aeronave, pouso real, sucesso de embarque ou recebimento de recompensa.
Por favor, confirme você mesmo as regras do jogo e os riscos da conta antes de usar; este projeto não fornece funções de desvio anti-trapaça.

## início rápido

Requer **Windows 10/11, Python 3.11+**, o jogo usa o modo de janela sem borda do monitor principal.

1. Baixe `PUBG-helper.zip` na versão mais recente](https://github.com/chenbinghan666/pubg-afk-helper/releases/latest) de [ ou clone este repositório.
2. Instale o Python e verifique **Adicione Python a PATH**.
3. Clique duas vezes em `install.cmd` e aguarde a conclusão da instalação da dependência.
4. Ao usá-lo pela primeira vez, clique duas vezes em **`preview.cmd`**, volte ao jogo e verifique o log de reconhecimento; este modo não envia entrada.
5. Após confirmar que o reconhecimento está correto, feche a visualização e clique duas vezes em **`launch.cmd`** para ativar a operação automática.

```powershell
git clone https://github.com/chenbinghan666/pubg-afk-helper.git
cd pubg-afk-helper
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe bot.py             # Apenas reconhecer
.\.venv\Scripts\python.exe bot.py --live      # Habilitar entrada
```

Os clones do Git leem `config.example.json` por padrão. Copie-o para `config.json` antes da customização e a configuração local não será enviada ao Git:

```powershell
Copy-Item config.example.json config.json
```

O warehouse vem com um conjunto de modelos de corte de botões para a interface do chinês tradicional. Se o idioma, a versão do jogo, a escala do HUD ou o layout forem diferentes, o modelo precisará ser regravado e não pode ser garantido que seja diretamente aplicável a todos os computadores.

## Processo padrão

```text
Identifique o salão → F começa a combinar
  → Desaparecimento do lobby detectado 3 vezes seguidas → espere 120 segundos
  → F Experimente saltar de paraquedas → vire à direita uma vez → W + Deslocamento Esquerdo
  → 30 segundos após o salto de paraquedas: olhando para o chão → Toque em F a cada 0,5 segundos
  → O minimapa fica estável por cerca de 1 segundo: tente cruzar, voltar/atravessar se necessário
  → Morte/Liquidação: botão de liberação → Voltar ao lobby → próxima rodada
```

O desaparecimento do lobby também pode ser uma tela de carregamento, o que não prova que você entrou na sala. Todos os tempos são ajustáveis.
O deslocamento padrão para curva à direita **4050** e o deslocamento para cima **5000** são apenas parâmetros de referência; o ângulo real depende da sensibilidade do jogo e das configurações do mouse.
A corrida e o salto Shift+C precisam ser consistentes com a tecla do jogo e as configurações de segurar/alternar.

## Chaves de operação

| Botão | função |
| --- | --- |
| **F8** | Pausa apenas, liberando as teclas mantidas pelo script |
| **F7** | Apenas continue |
| **F9** | Saia e solte a chave |
| **Ctrl+C** | Parar o programa no terminal |

A entrada é pausada ao sair do jogo e será retomada automaticamente após voltar; a contagem regressiva iniciada ainda é calculada com base no tempo real decorrido.
A pausa no canto do mouse é desativada por padrão para evitar a proteção automática do acionador e pode ser ativada individualmente com `mouse_corner_pause`.
A limpeza por pressionamento de tecla não pode ser executada quando o processo é encerrado à força ou o computador é desligado.

## Configuração e solução de problemas

Para parâmetros completos, comandos de gravação de modelo, área relativa do minimapa e método de calibração de sensibilidade, consulte o Manual de Configuração e Uso do [](../../docs/CONFIGURATION.md).

| pergunta | Verificação de prioridade |
| --- | --- |
| Nenhum reconhecimento ou ação | Se a janela superior mostra uma pausa, se o jogo está em primeiro plano e se o título da janela contém `PUBG` |
| Falha no reconhecimento de início ou liquidação | Se o idioma da interface, a resolução e a escala do HUD correspondem ao modelo |
| Skydive muito cedo/muito tarde | `movement.jump_delay_seconds` |
| Levantar cedo demais/olhar para baixo na direção errada | `pickup_delay_after_jump_seconds`, `look_down_pixels` e configurações de reversão do eixo Y |
| Ângulo de giro à direita errado | Calibrar de acordo com o ângulo de rotação real `turn_right_pixels` |
| Correr ou pular não tem efeito | Atalhos de teclas, modo de espera, permissões de execução e se o jogo aceita entrada analógica |
| Erro de julgamento/falta de parede anti-bloqueio | Indicadores de escala estáveis para área do minimapa, zoom, configurações de rotação e janelas aéreas |

O log é gravado no `bot.log` local. Remova conta, bate-papo, caminho privado e outras informações antes de dar feedback.

## desenvolver

```powershell
.\.venv\Scripts\python.exe -m unittest -v
.\.venv\Scripts\python.exe package.py
```

O teste simula a entrada do teclado e do mouse sem operar o jogo. A versão pública gera automaticamente imagens sintéticas para teste; se existir localmente
`reference_screens/`, você pode usar as capturas de tela de referência pessoal correspondentes para regressão adicional. Este diretório não está incluído no warehouse ou no pacote de distribuição.
CI executa testes no Windows usando Python 3.11 e 3.12.
Os testes offline não podem substituir a verificação de jogos reais em diferentes hardwares, versões de jogos e sensibilidades.

Arquivos principais: `bot.py` é a máquina de estado, reconhecimento e implementação de entrada, `status_overlay.py` é a janela de status,
`prepare_templates.py` é uma ferramenta de geração de modelo de cinco interfaces e `package.py` é um script de construção de pacote de distribuição.

Bem-vindo ao relatar problemas reproduzíveis por meio de [Issues](https://github.com/chenbinghan666/pubg-afk-helper/issues).
Leia as instruções de contribuição [](../../CONTRIBUTING.md) antes de enviar alterações. Para registros de versão, consulte [CHANGELOG](../../CHANGELOG.md).

## licença

O código e a documentação originais são licenciados sob a Licença [MIT](../../LICENSE). O corte, o nome e a marca registrada da interface do jogo ainda pertencem aos seus respectivos detentores de direitos. Consulte a declaração de terceiros [](../../NOTICE.md) para obter detalhes. Este projeto não possui afiliação ou parceria oficial com KRAFTON/PUBG.
