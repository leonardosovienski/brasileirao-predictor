# Validação sintética da publicação

Roteiro portátil criado em 10/09/2026 para reproduzir as 336 regressões RES e nove verificações do isolamento. `scope.json` é a lista explícita de testes revisados. Não representa CI global, homologação comercial, avaliação econômica ou permissão de capital.

No checkout, instale a cadeia de dependências fixada com `uv sync --locked --all-extras`. Em seguida, execute o Python desse ambiente com `-I -B tools/publication_validation/run.py DIRETORIO_NOVO_FORA_DO_CHECKOUT`. No Windows mantenha a saída em `C:/BRASILEIRAO/work`. O runner limpa o ambiente, bloqueia rede, subprocessos e conteúdo operacional, e limita escritas à saída. Os nove probes tentam transgredir essas fronteiras e devem ser recusados; suas recusas aparecem no recibo. É uma proteção contra efeitos acidentais dos testes revisados, não uma sandbox contra código hostil.

`publication-validation.yml` executa essa lista em Python 3.13/3.14, .NET completo com Redis descartável e os mesmos mínimos de cobertura .NET (80% linhas/ramos), além do Compose com volumes próprios, feed externo vazio e configuração sintética. Não reduz nem substitui os gates do `ci.yml` original. O runtime Linux descartável está no GitHub; os arquivos e recibos locais ficam em C:/BRASILEIRAO.

A CI global importa avaliadores H14/H15/A1 e lê registros reais em testes como `test_core3_harness_contract.py` e `test_trials_registry_schema.py`. Sua execução permanece incompatível com o mandato consolidado. A publicação usa uma branch temporária `publication-validation-*`; a integração em main deve levar `[skip ci]` e registrar explicitamente que a CI global não foi executada. O workflow delimitado também pode ser disparado manualmente em uma revisão escolhida. Não inferir homologação global a partir de um resultado verde deste workflow.

`compose_config.py` resolve somente a estrutura do Compose, substitui o bind de config sem ler sua origem, rejeita mounts inesperados e mantém apenas fixtures revisadas. A aplicação operacional e seus volumes não são usados. Falhas devem ser preservadas e corrigidas, sem reduzir critérios para obter aprovação.
