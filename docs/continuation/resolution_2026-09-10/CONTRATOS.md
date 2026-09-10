# Contratos corrigidos — RES-20260910

Código desta etapa usa dados declarados pelo produtor. Validação de tipos, clocks e hashes não autentica a fonte nem comprova aceitação comercial. Capital permanece desabilitado.

## Persistência temporal

`data/pit_backfill.py` grava `pit-curated/2.0` em banco novo. Partidas preservam revisões por recebimento/proveniência e status; preços preservam período, linha e estados sem preço. Uma leitura as-of seleciona a revisão conhecida antes do corte; cancelamento ou conflito não recupera a versão anterior. Banco curated/1 é recusado sem migração implícita ou alteração dos bytes. Não houve migração operacional.

`data/lineup_envelopes.py` oferece `lineup-envelope/2`: fonte, evento, equipe, parser, hash do raw, observação, recebimento, publicação opcional, status e jogadores. `COMPLETE`, `EMPTY`, `REMOVED`, `UNAVAILABLE` e `INVALID` são distintos. Arquivos imutáveis são publicados após flush/fsync com criação exclusiva por hard link; retries idênticos não sobrescrevem. Sistemas de arquivos sem hard links falham explicitamente. A leitura confere nome/hash/JSON canônico e rejeita corrupção. Conflitos no último relógio são recusados; uma revisão posterior resolve conflitos antigos. Na projeção para titulares, equipes desconhecidas são omitidas; vazias/removidas recebem conjunto vazio. Os envelopes completos preservam a distinção. O coletor legado compartilhado não foi alterado.

## Dataset e replay condicionais

`materialize_total_market_records` exige `offer_bookmaker` explícito, mercado FT e linha de meio gol. Usa oferta completa dessa casa e referência de outras casas. A política de referência mantém remoção proporcional somente em pares com margem positiva. Relógios de observação, disponibilidade e recebimento são obrigatórios, com limites de idade e simultaneidade dentro e entre casas. Último estado suspenso impede recuperação de preço antigo. Contexto de features exige disponibilidade e valores explícitos; falta de contexto causa `ABSTAIN_DATA`.

O universo inclui todos os eventos fornecidos nesse mercado, inclusive sem preço ou resultado. Eventos nunca fornecidos não são recuperados. Gols exigem contagens inteiras não negativas; pendência não vira derrota. Revisões conflitantes de kickoff devem ser reconciliadas antes da materialização. Dados com apenas last-update não provam recebimento histórico e são inadmissíveis. Proveniência das ofertas e referências usadas acompanha cada registro admitido.

`evaluate_walkforward` ordena decisões, exige predição anterior ao kickoff e liquidação posterior, preserva abstinências e treina somente com labels disponíveis antes do bloco. Sem clock de disponibilidade do label, o relógio de liquidação fornecido é uma hipótese declarada; o relatório não certifica a causalidade histórica da fonte. Features futuras, valores não finitos, labels inválidos e eventos duplicados são recusados antes de treinar.

`shadow_portfolio` usa stake como fração da banca inicial, reserva stake e custo antes de apostar, recusa capital insuficiente e devolve principal somente no relógio de liquidação. Ordens simultâneas têm prioridade determinística pelo evento, sem usar o resultado. Posições pendentes mantêm capital preso e ROI final desconhecido. A contabilidade reconcilia caixa, principal aberto, retornos e custos. Implementa apenas back binário e custo plano declarado; preenchimento completo é hipótese. Não implementa lay, asiáticos, câmbio, aceitação, tributos pessoais ou custos de infraestrutura observados.

`residual_gate` conta eventos distintos no mínimo amostral. PSR é diagnóstico sobre retornos médios por evento, sem afirmar independência temporal. DSR fornecido pelo chamador não promove candidato. Um resultado favorável exige `PENDING_DESIGN`: inventário registrado de tentativas e desenho temporal pré-especificado. Isso corrige a aprovação indevida; não inventa o histórico de tentativas ausente.

## Worker e mercado

O modo normal exige `LineupModelInputs`: identidade do jogo/equipes, versão, Elo de cada lado, hash do VORP carregado, `LearnedThrough`, `FittedAt`, `AvailableAt`, `KickoffAt` e posições GK/DF/MF/FW de todos os titulares. O Worker recusa contexto futuro, hash divergente, cobertura VORP ausente e mistura de contextos entre lados. Estes campos são declarações de procedência, não autenticação externa do treinamento. A posição explicitamente declarada pode usar seu replacement level; posição desconhecida não recebe zero automaticamente.

Somente `Worker:AllowSyntheticInputs=true` permite Elo 1500/1500 e posição UNKNOWN para demonstração. No Compose, a variável é `LINEUP_ALLOW_SYNTHETIC_INPUTS`, falsa por padrão. A CI declara esse modo porque usa fixtures sintéticas. O teste entre processos termina imports/JIT antes de criar sua cotação sintética e medir recuperação de mensagens.

Feed vazio fica desativado. Para um produtor real, a configuração exige `EXCHANGE_WEBSOCKET_URL` WSS, `EXCHANGE_PROTOCOL=normalized-market/v1`, `EXCHANGE_SOURCE` e `EXCHANGE_BOOKMAKER`; o Compose mapeia para o prefixo `LINEUP_Exchange__`. URL não pode conter credenciais, query ou fragmento. A chave opcional vai em cabeçalho e não aparece nos logs.

Mensagem normalizada: `schema_version`, `match_id`, `source`, `bookmaker`, `period=FT`, `status`, revisão inteira não negativa, `observed_at`, `available_at`, `kickoff_at` com timezone e preços decimais `home/draw/away` para estado ACTIVE. OU2.5 opcional usa `over25/under25` e `line=2.5`. Estados SUSPENDED/CLOSED não precisam de preços ativos. Há limite de mensagem de 256KiB e 10 mil identidades; erro de contrato retira o preço identificado. Revisão antiga, conflito e desconexão não renovam uma oferta antiga. Idade máxima permanece 30 segundos.

O serviço espera uma ponte que implemente esse contrato. Nenhuma conexão comercial ou aceitação foi comprovada nesta etapa. Mensagem legada somente entra quando `Exchange:AllowSyntheticPayloads=true`, recebendo marca sintética. Esse modo não é ativado no Compose padrão.

## Banca e recuperação

`bank_state` lê banca e ledger sob os mesmos locks usados pelos escritores, em ordem canônica. A unidade de cada aposta vem do regime declarado no instante do registro. Troca posterior de unidade não reavalia o passado. Regime ausente, ambíguo ou troca de moeda sem câmbio produz reconciliação pendente, sem saldo monetário fabricado. Drawdown considera aportes/retiradas; ambiguidade temporal de fluxo e liquidação impede NAV definitivo. O livro continua manual e não certifica custos ou execução comercial.

`restore_backup` verifica a origem, copia para raiz inexistente e verifica novamente destino e manifesto esperado antes de retornar sucesso. O manifesto é mantido. Cópia inválida fica preservada para diagnóstico e não é declarada restaurada. O teste usa SQLite e arquivos sintéticos. Backup de vários arquivos não é uma transação global; o ensaio não restaura coortes, credenciais, serviços externos nem o computador inteiro.

## Compatibilidade e caminhos retirados da admissão econômica

Curated/1 e a API antiga de materialização exigem adaptação explícita. O novo arquivo de escalação é um sucessor opt-in, sem migração silenciosa do coletor protegido. O replay OU2.5 legado, seu ancoramento na própria oferta e as interfaces de cache/joins históricos compartilhados permanecem preservados como pesquisa histórica; não são o caminho autorizado para nova prova de vantagem. Relatórios congelados continuam com seus valores originais e escopo datado.

## Outros contratos corrigidos

O entrypoint instalado brasileirao-kernel usa kernel_cli:main. --healthcheck exige caminhos/configuração válidos (erro de argumentos = 2), consulta Redis sem importar NumPy/Numba/modelo/DB, usa limites de conexão/leitura e retorna 1 se indisponível. Logs mostram somente classe da exceção. PubSub mantém no máximo 32 handlers, com poller durável limitado separadamente a 32; não é um limite global de 32. Parâmetros do kernel são validados antes de cliente/JIT, com grade inteira de 1 a 100 e valores finitos.

Player stats v2 conserva available_at pós-jogo ou desconhecido, sem convertê-lo em instante pré-jogo. Promovidos exigem inteiros, equipes/posições únicas, quatro promovidos por temporada e JSON sem chaves repetidas. O detector estrutural exige preço soft e referência dentro da idade admitida, odds imutáveis e parâmetros finitos; o solver power expande o bracket. Fontes antigas de clocks continuam limitadas.

O importador OU2.5 v3 exige caminho de DB inexistente; lê/hash/parseia os mesmos bytes, rejeita odds não finitas/<=1 e contagens fracionárias/inválidas. Publica por hard link exclusivo somente após integrity_check e fsync do temporário próprio. Falhas deixam temporário preservado; não há importação operacional implícita. Backup recusa symlink/junction e destino dentro da árvore copiada; URI SQLite usa Path.as_uri e manifesto é verificado também no destino.

odds_shop não carrega configuração no import. Modo online exige clocks conhecidos e mercados completos com casas únicas; --from-file não pode disparar --tempos online. A saída é diagnóstico, não recomenda aposta nem anuncia janela economicamente validada. Uso de API metered continua condicionado a plano/quota/reserva verificados antes de executar a CLI; ela não foi usada para coleta nesta etapa.

Liquidação diagnóstica v2 exige source_event_id correspondente, placares inteiros não negativos e probabilidades finitas normalizadas. Hash da previsão vincula os fatos; fact_hash separa resultado de settled_at e content_hash protege recibo. Writer lock coordena autores cooperantes; retry idêntico mantém o primeiro recibo, conflito é rejeitado. Registros v1 não são migrados automaticamente e precisam de conciliação explícita. Não há execução financeira ou liquidação de coortes.

coverage_report exige presença de todas as fontes definidas, medição branch e contagens inteiras coerentes. Zero denominador é N/A. Inclui kernel_cli e kernel_redis_v2. A cobertura .NET não é hardcoded; exige recibo separado. Não foi afirmado que todo o gate Python passou nesta revisão parcial.

Retry da liquidação diagnóstica devolve a linha persistida também ao stdout/run-log; append_settlement mantém sua API booleana e record_settlement retorna (inserido, recibo). Leitura e append desse recibo compartilham writer lock.
