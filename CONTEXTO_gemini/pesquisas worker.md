# **Pesquisa Aprofundada: Solução para Problemas de Worker Celery com PostgreSQL ENUM**

## **Análise Completa do Problema**

Com base na pesquisa realizada, identifiquei que sua análise está **completamente correta**. O problema central é uma **dessincronização crítica entre o schema PostgreSQL e o código SQLAlchemy**, especificamente relacionada ao gerenciamento de tipos ENUM em schemas customizados.

## **Causa Raiz Confirmada**

## **1\. Problema de Schema Inheritance**

O SQLAlchemy **não herda automaticamente o schema** para tipos ENUM quando definidos de forma simplificada. O parâmetro `inherit_schema=False` é o padrão atual (mudando para `True` na versão 2.1), causando:[github+1](https://github.com/sqlalchemy/sqlalchemy/discussions/10583)​

python  
*`# Problema atual - ENUM criado no schema 'public' por padrão`*  
`status: Mapped[IngestionStatus]  # Schema não herdado`

*`# Solução correta`*  
`status: Mapped[IngestionStatus] = mapped_column(`  
    `sqlalchemy.Enum(IngestionStatus, inherit_schema=True)`  
`)`

## **2\. Falha do Base.metadata.drop\_all()**

O `drop_all()` **falha silenciosamente** ao tentar remover tipos ENUM PostgreSQL:[stackoverflow+1](https://stackoverflow.com/questions/24258921/how-do-i-drop-custom-types-using-sqlalchemy-postgresql)​

* Tipos ENUM são objetos independentes no PostgreSQL

* `create_type=False` impede criação/remoção automática[stackoverflow+1](https://stackoverflow.com/questions/32761486)​

* Dependências de tabela bloqueiam remoção sem `CASCADE`[postgresql+1](https://docs.postgresql.tw/11/reference/sql-commands/drop-type)​

## **Soluções Práticas Implementáveis**

## **Solução 1: Correção Imediata \- Schema Inheritance**

**Em `core/models.py`:**

python  
`from sqlalchemy import Column, Enum`  
`from sqlalchemy.dialects.postgresql import ENUM`

`class IngestionQueue(Base):`  
    `__tablename__ = 'ingestion_queue'`  
    `__table_args__ = {'schema': 'ai'}`  
      
    `# Correção principal - forçar herança de schema`  
    `status = Column(`  
        `Enum(IngestionStatus, inherit_schema=True),`  
        `nullable=False`  
    `)`

## **Solução 2: Remoção Forçada do ENUM Conflitante**

**Via DBeaver/psql:**

sql  
*`-- Primeiro, verificar estado atual`*  
`SELECT enumlabel`   
`FROM pg_enum`   
`WHERE enumtypid = (`  
    `SELECT oid FROM pg_type WHERE typname = 'ingestionstatus'`  
`);`

*`-- Remoção forçada com CASCADE`*  
`DROP TYPE IF EXISTS ai.ingestionstatus CASCADE;`  
`DROP TYPE IF EXISTS public.ingestionstatus CASCADE;`

*`-- Verificar se todos foram removidos`*  
`SELECT typname, nspname`   
`FROM pg_type t`   
`JOIN pg_namespace n ON t.typnamespace = n.oid`   
`WHERE typname = 'ingestionstatus';`

## **Solução 3: Migração Robusta com Alembic**

**Criar nova migração manual:**

python  
`"""Fix enum schema issues`

`Revision ID: fix_enum_schema`  
`"""`  
`from alembic import op`  
`import sqlalchemy as sa`

`def upgrade():`  
    `# Remover tipos conflitantes`  
    `op.execute("DROP TYPE IF EXISTS ai.ingestionstatus CASCADE")`  
    `op.execute("DROP TYPE IF EXISTS public.ingestionstatus CASCADE")`  
      
    `# Criar tipo correto no schema 'ai'`  
    `op.execute("""`  
        `CREATE TYPE ai.ingestionstatus AS ENUM (`  
            `'pending', 'processing', 'completed', 'failed'`  
        `)`  
    `""")`  
      
    `# Recriar tabela se necessário`  
    `# (SQLAlchemy criará com referência correta ao tipo)`

`def downgrade():`  
    `op.execute("DROP TYPE IF EXISTS ai.ingestionstatus CASCADE")`

## **Alternativas Recomendadas**

## **Opção A: VARCHAR com CHECK Constraint**

Para evitar complexidade de ENUMs nativos:[news.ycombinator+1](https://news.ycombinator.com/item?id=36403087)​

python  
`from sqlalchemy import String, CheckConstraint`

`class IngestionQueue(Base):`  
    `__tablename__ = 'ingestion_queue'`  
    `__table_args__ = (`  
        `CheckConstraint(`  
            `"status IN ('pending', 'processing', 'completed', 'failed')",`  
            `name='ck_ingestion_status'`  
        `),`  
        `{'schema': 'ai'}`  
    `)`  
      
    `status = Column(String(20), nullable=False)`

**Vantagens:**

* Sem problemas de schema

* Fácil migração com Alembic[making.close](https://making.close.com/posts/native-enums-or-check-constraints-in-postgresql)​

* Performance similar[making.close](https://making.close.com/posts/native-enums-or-check-constraints-in-postgresql)​

* Menos complexidade operacional

## **Opção B: Enum com Metadata Explícita**

python  
`from sqlalchemy import MetaData`

`metadata_ai = MetaData(schema="ai")`

`class Base(DeclarativeBase):`  
    `metadata = metadata_ai`

*`# Em models.py`*  
`status = Column(`  
    `Enum(IngestionStatus, metadata=metadata_ai),`  
    `nullable=False`  
`)`

## **Correção dos Problemas AsyncIO**

## **Worker Configuration**

python  
*`# celery_config.py`*  
`worker_pool = 'gevent'  # Em vez de 'prefork'`  
`worker_disable_rate_limits = True`

*`# Para prevenir event loop corruption`*  
`import asyncio`  
`asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`

## **Session Management Fix**

python  
*`# worker_service/tasks.py`*  
`@celery_app.task(bind=True)`  
`def poll_and_process_jobs(self):`  
    `try:`  
        `# Single asyncio.run() call`  
        `return asyncio.run(process_jobs_logic())`  
    `except Exception as exc:`  
        `# Proper cleanup`  
        `if hasattr(exc, '__cause__') and 'event loop' in str(exc.__cause__):`  
            `# Reset connection pool`  
            `AsyncSessionFactory.registry.clear()`  
        `raise`

## **Verificação e Diagnóstico**

## **Comandos de Verificação**

sql  
*`-- 1. Verificar todos os ENUMs existentes`*  
`SELECT t.typname as enum_name,`   
       `n.nspname as schema_name,`  
       `string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) as values`  
`FROM pg_type t`   
`JOIN pg_enum e ON t.oid = e.enumtypid`    
`JOIN pg_namespace n ON n.oid = t.typnamespace`  
`WHERE t.typname = 'ingestionstatus'`  
`GROUP BY t.typname, n.nspname;`

*`-- 2. Verificar search_path atual`*  
`SHOW search_path;`  
`SELECT current_schemas(false);`

*`-- 3. Testar acesso qualificado`*  
`SELECT 'processing'::ai.ingestionstatus;`

## **Script de Validação Python**

python  
`def validate_enum_setup():`  
    `"""Validar configuração do ENUM antes do worker"""`  
    `from sqlalchemy import text`  
    `from core.database import engine`  
      
    `with engine.connect() as conn:`  
        `# Verificar se tipo existe no schema correto`  
        `result = conn.execute(text("""`  
            `SELECT EXISTS(`  
                `SELECT 1 FROM pg_type t`   
                `JOIN pg_namespace n ON t.typnamespace = n.oid`   
                `WHERE t.typname = 'ingestionstatus' AND n.nspname = 'ai'`  
            `)`  
        `"""))`  
          
        `if not result.scalar():`  
            `raise RuntimeError("ENUM ai.ingestionstatus não encontrado!")`  
          
        `# Testar valores`  
        `values = conn.execute(text("""`  
            `SELECT unnest(enum_range(NULL::ai.ingestionstatus))`  
        `""")).fetchall()`  
          
        `expected = {'pending', 'processing', 'completed', 'failed'}`  
        `actual = {v[0] for v in values}`  
          
        `if expected != actual:`  
            `raise RuntimeError(f"Valores ENUM incorretos. Esperado: {expected}, Atual: {actual}")`

## **Implementação Recomendada**

## **Sequência de Correção**

1. **Backup da base atual**

2. **Implementar validação**: Execute script de diagnóstico

3. **Correção do modelo**: Adicionar `inherit_schema=True`

4. **Limpeza manual**: `DROP TYPE ... CASCADE`

5. **Recriação**: `python init_db.py`

6. **Validação**: Executar testes do worker

7. **Monitoramento**: Logs detalhados por 24h

## **Prevenção Futura**

* **Sempre usar** `inherit_schema=True` com schemas customizados[github+1](https://github.com/sqlalchemy/sqlalchemy/issues/10594)​

* **Preferir Alembic** para mudanças de schema[makimo+1](https://makimo.com/blog/upgrading-postgresqls-enum-type-with-sqlalchemy-using-alembic-migration/)​

* **Implementar validação** de schema em CI/CD

* **Considerar VARCHAR \+ CHECK** para casos simples[making.close](https://making.close.com/posts/native-enums-or-check-constraints-in-postgresql)​

A pesquisa confirmou que sua análise estava precisa. O problema é amplamente documentado na comunidade SQLAlchemy, com soluções bem estabelecidas. A correção principal é **forçar a herança de schema** combinada com **limpeza manual dos tipos conflitantes**.

1. [https://github.com/sqlalchemy/sqlalchemy/discussions/10583](https://github.com/sqlalchemy/sqlalchemy/discussions/10583)  
2. [https://github.com/sqlalchemy/sqlalchemy/issues/10594](https://github.com/sqlalchemy/sqlalchemy/issues/10594)  
3. [https://stackoverflow.com/questions/24258921/how-do-i-drop-custom-types-using-sqlalchemy-postgresql](https://stackoverflow.com/questions/24258921/how-do-i-drop-custom-types-using-sqlalchemy-postgresql)  
4. [https://stackoverflow.com/questions/32761486](https://stackoverflow.com/questions/32761486)  
5. [https://docs.postgresql.tw/11/reference/sql-commands/drop-type](https://docs.postgresql.tw/11/reference/sql-commands/drop-type)  
6. [https://www.pgtutorial.com/postgresql-tutorial/postgresql-drop-type/](https://www.pgtutorial.com/postgresql-tutorial/postgresql-drop-type/)  
7. [https://news.ycombinator.com/item?id=36403087](https://news.ycombinator.com/item?id=36403087)  
8. [https://making.close.com/posts/native-enums-or-check-constraints-in-postgresql](https://making.close.com/posts/native-enums-or-check-constraints-in-postgresql)  
9. [https://makimo.com/blog/upgrading-postgresqls-enum-type-with-sqlalchemy-using-alembic-migration/](https://makimo.com/blog/upgrading-postgresqls-enum-type-with-sqlalchemy-using-alembic-migration/)  
10. [https://github.com/imankulov/alembic-enums](https://github.com/imankulov/alembic-enums)  
11. [https://arxiv.org/pdf/2404.08525.pdf](https://arxiv.org/pdf/2404.08525.pdf)  
12. [http://arxiv.org/pdf/2403.09706.pdf](http://arxiv.org/pdf/2403.09706.pdf)  
13. [https://aclanthology.org/2023.emnlp-main.868.pdf](https://aclanthology.org/2023.emnlp-main.868.pdf)  
14. [https://arxiv.org/pdf/2312.00638.pdf](https://arxiv.org/pdf/2312.00638.pdf)  
15. [https://www.aclweb.org/anthology/E17-1058.pdf](https://www.aclweb.org/anthology/E17-1058.pdf)  
16. [https://arxiv.org/html/2411.17603v1](https://arxiv.org/html/2411.17603v1)  
17. [https://arxiv.org/pdf/2412.06269.pdf](https://arxiv.org/pdf/2412.06269.pdf)  
18. [https://arxiv.org/pdf/2204.06670.pdf](https://arxiv.org/pdf/2204.06670.pdf)  
19. [https://bobcares.com/blog/error-type-enum-does-not-exist/](https://bobcares.com/blog/error-type-enum-does-not-exist/)  
20. [https://pypi.org/project/alembic-enums/](https://pypi.org/project/alembic-enums/)  
21. [https://github.com/npgsql/npgsql/issues/6148](https://github.com/npgsql/npgsql/issues/6148)  
22. [https://www.pingcap.com/article/best-practices-alembic-schema-migration/](https://www.pingcap.com/article/best-practices-alembic-schema-migration/)  
23. [https://stackoverflow.com/questions/2676133/best-way-to-do-enum-in-sqlalchemy](https://stackoverflow.com/questions/2676133/best-way-to-do-enum-in-sqlalchemy)  
24. [https://github.com/npgsql/efcore.pg/issues/2963](https://github.com/npgsql/efcore.pg/issues/2963)  
25. [https://stackoverflow.com/questions/68381060/is-it-possible-to-cast-from-one-enum-to-another-in-postgresql](https://stackoverflow.com/questions/68381060/is-it-possible-to-cast-from-one-enum-to-another-in-postgresql)  
26. [https://blog.wrouesnel.com/posts/sqlalchemy-enums-careful-what-goes-into-the-database/](https://blog.wrouesnel.com/posts/sqlalchemy-enums-careful-what-goes-into-the-database/)  
27. [https://www.postgresql.org/docs/current/sql-altertype.html](https://www.postgresql.org/docs/current/sql-altertype.html)  
28. [https://pypi.org/project/alembic-postgresql-enum/](https://pypi.org/project/alembic-postgresql-enum/)  
29. [https://www.sqlalchemy.org/docs/21/changelog/migration\_21.html](https://www.sqlalchemy.org/docs/21/changelog/migration_21.html)  
30. [https://www.postgresql.org/docs/current/functions-enum.html](https://www.postgresql.org/docs/current/functions-enum.html)  
31. [https://stackoverflow.com/questions/63461381/how-to-use-an-existing-sqlalchemy-enum-in-an-alembic-migration-postgres](https://stackoverflow.com/questions/63461381/how-to-use-an-existing-sqlalchemy-enum-in-an-alembic-migration-postgres)  
32. [https://groups.google.com/g/sqlalchemy/c/HqI3OizHBG4](https://groups.google.com/g/sqlalchemy/c/HqI3OizHBG4)  
33. [https://community.forestadmin.com/t/postgresql-enum-type-does-not-exist-error-wrong-enum-type-name/5931](https://community.forestadmin.com/t/postgresql-enum-type-does-not-exist-error-wrong-enum-type-name/5931)  
34. [https://dokk.org/documentation/sqlalchemy/rel\_1\_3\_24/dialects/postgresql/](https://dokk.org/documentation/sqlalchemy/rel_1_3_24/dialects/postgresql/)  
35. [https://pydoc.dev/sqlalchemy/latest/sqlalchemy.dialects.postgresql.ENUM.html](https://pydoc.dev/sqlalchemy/latest/sqlalchemy.dialects.postgresql.ENUM.html)  
36. [https://docs-sqlalchemy.readthedocs.io/ko/latest/dialects/postgresql.html](https://docs-sqlalchemy.readthedocs.io/ko/latest/dialects/postgresql.html)  
37. [https://www.mbeckler.org/blog/?p=218](https://www.mbeckler.org/blog/?p=218)  
38. [https://www.semanticscholar.org/paper/9eecfa9e28c3e96bad7de72af8da8e5eef202600](https://www.semanticscholar.org/paper/9eecfa9e28c3e96bad7de72af8da8e5eef202600)  
39. [https://www.aclweb.org/anthology/2020.acl-main.677.pdf](https://www.aclweb.org/anthology/2020.acl-main.677.pdf)  
40. [http://arxiv.org/pdf/2406.14545.pdf](http://arxiv.org/pdf/2406.14545.pdf)  
41. [https://arxiv.org/pdf/1911.04942.pdf](https://arxiv.org/pdf/1911.04942.pdf)  
42. [https://arxiv.org/pdf/2111.12835.pdf](https://arxiv.org/pdf/2111.12835.pdf)  
43. [https://arxiv.org/html/2411.13278v1](https://arxiv.org/html/2411.13278v1)  
44. [http://arxiv.org/pdf/2501.17174.pdf](http://arxiv.org/pdf/2501.17174.pdf)  
45. [http://arxiv.org/pdf/1602.03501.pdf](http://arxiv.org/pdf/1602.03501.pdf)  
46. [http://arxiv.org/pdf/1608.05564.pdf](http://arxiv.org/pdf/1608.05564.pdf)  
47. [https://stackoverflow.com/questions/25932327/how-to-swap-the-postgres-schema-attribute-for-a-sqlalchemy-metadata](https://stackoverflow.com/questions/25932327/how-to-swap-the-postgres-schema-attribute-for-a-sqlalchemy-metadata)  
48. [https://www.postgresql.org/docs/current/ddl-schemas.html](https://www.postgresql.org/docs/current/ddl-schemas.html)  
49. [https://stackoverflow.com/questions/61224799/sqlalchemy-raises-error-when-inserting-postgres-array-of-enum-column](https://stackoverflow.com/questions/61224799/sqlalchemy-raises-error-when-inserting-postgres-array-of-enum-column)  
50. [https://www.postgresonline.com/article\_pfriendly/279.html](https://www.postgresonline.com/article_pfriendly/279.html)  
51. [https://stackoverflow.com/questions/66437766/how-to-use-enum-with-schema-in-sqlalchemy](https://stackoverflow.com/questions/66437766/how-to-use-enum-with-schema-in-sqlalchemy)  
52. [https://stackoverflow.com/questions/22812840/postgres-cannot-find-enum-type-if-prepended-by-schema-name](https://stackoverflow.com/questions/22812840/postgres-cannot-find-enum-type-if-prepended-by-schema-name)  
53. [https://github.com/launchbadge/sqlx/issues/2114](https://github.com/launchbadge/sqlx/issues/2114)  
54. [https://github.com/sqlalchemy/sqlalchemy/discussions/7181](https://github.com/sqlalchemy/sqlalchemy/discussions/7181)  
55. [https://www.mayn.es/post/2021-04-03-dynamically-set-schemas-sqlalchemy/](https://www.mayn.es/post/2021-04-03-dynamically-set-schemas-sqlalchemy/)  
56. [https://blog.bigsmoke.us/2022/11/11/postgresql-schema-search\_path](https://blog.bigsmoke.us/2022/11/11/postgresql-schema-search_path)  
57. [https://groups.google.com/g/sqlalchemy/c/HS-emAGDJ64/m/FzGhjeFjFQAJ](https://groups.google.com/g/sqlalchemy/c/HS-emAGDJ64/m/FzGhjeFjFQAJ)  
58. [https://supabase.com/docs/guides/database/postgres/enums](https://supabase.com/docs/guides/database/postgres/enums)  
59. [https://www.crunchydata.com/blog/demystifying-schemas-search\_path-through-examples](https://www.crunchydata.com/blog/demystifying-schemas-search_path-through-examples)  
60. [https://groups.google.com/g/sqlalchemy/c/HS-emAGDJ64](https://groups.google.com/g/sqlalchemy/c/HS-emAGDJ64)  
61. [https://groups.google.com/g/sqlalchemy-alembic/c/4Df8aXcurCk](https://groups.google.com/g/sqlalchemy-alembic/c/4Df8aXcurCk)  
62. [https://github.com/jOOQ/jOOQ/issues/10277](https://github.com/jOOQ/jOOQ/issues/10277)  
63. [https://news.ycombinator.com/item?id=36404617](https://news.ycombinator.com/item?id=36404617)  
64. [https://stackoverflow.com/questions/2875610/permanently-set-postgresql-schema-path](https://stackoverflow.com/questions/2875610/permanently-set-postgresql-schema-path)

Perfeito — fiz uma nova rodada de pesquisa focada em **ENUM do PostgreSQL \+ SQLAlchemy (2.0) \+ Alembic \+ schemas** e no porquê do `ai.ingestionstatus` “sumir” / ficar inconsistente. Seguem **achados objetivos** e um **plano de correção definitivo**.

---

# **Achados (o que a doc e a prática realmente dizem)**

1. **SQLAlchemy Enum e schemas (“ai”)**

* O `sqlalchemy.types.Enum` é um `SchemaType`. Para que o **CREATE TYPE** aconteça via `create_all()`, o `Enum` precisa estar **associado a um MetaData** (via `metadata=...`) e/ou ter **`schema="ai"`** (ou `inherit_schema=True` para herdar do `Table`). Caso contrário, ele tenta criar o tipo “no voo” quando a tabela é criada — e isso costuma falhar/sumir em projetos multi-schema. Além disso, o `Enum` **herda** `MetaData.schema` se você o passar via `metadata=Base.metadata`. ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/core/type_basics.html))

2. **Por padrão, o SQLAlchemy persiste o *nome* do Enum Python (ex.: `PROCESSING`) e não o *valor* (`"processing"`)**

* Se você quer gravar `"processing"` (minúsculo) no Postgres, use **`values_callable=lambda e: [m.value for m in e]`** (e defina o `Enum` Python com `.value` nos literais). Sem isso, você verá labels em MAIÚSCULAS no tipo nativo. ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/core/type_basics.html))

3. **`native_enum=False` transforma a coluna em `VARCHAR` \+ (opcional) CHECK, não cria TYPE**

* Se você põe `native_enum=False`, **não haverá** tipo `ai.ingestionstatus` no banco; qualquer `CAST(... AS ai.ingestionstatus)` em SQL bruto **quebra** com `UndefinedObjectError`. Use nativo **ou** remova `CAST` e trate como texto com constraint. ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/core/type_basics.html))

4. **Inspeção e diagnóstico no próprio Postgres**

* Para listar labels do tipo: `SELECT enum_range(NULL::ai.ingestionstatus);` (ordem original). Também é simples inspecionar em baixo nível via `pg_enum/pg_type/pg_namespace`. ([PostgreSQL](https://www.postgresql.org/docs/current/functions-enum.html?utm_source=chatgpt.com))

* `DROP TYPE ... [CASCADE]` remove o tipo (cuidado com dependências). ([PostgreSQL](https://www.postgresql.org/docs/current/sql-droptype.html?utm_source=chatgpt.com))

* Adição/renome de labels: `ALTER TYPE ... ADD VALUE [IF NOT EXISTS] [BEFORE|AFTER]` / `RENAME VALUE`. **Remover** label **não é suportado** sem recriar o tipo. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-altertype.html?utm_source=chatgpt.com))

5. **Alembic: enums são “especiais”**

* O caminho padrão de mercado é **migrar ENUMs por DDL explícito**: `op.execute("ALTER TYPE ... ADD VALUE ...")` ou a estratégia **v2 → RENAME** quando precisa **remover/reordenar** labels. (Não há “DROP VALUE”.) ([PostgreSQL](https://www.postgresql.org/docs/current/sql-altertype.html?utm_source=chatgpt.com))

* Ferramentas/receitas: `PGInspector.get_enums()` para refletir enums; bibliotecas como **alembic-postgresql-enum** ajudam a autogerar alterações (use com critério). ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/dialects/postgresql.html?utm_source=chatgpt.com))

6. **`search_path` pode te derrubar**

* Objetos não qualificados (ex.: `CAST(:x AS ingestionstatus)`) podem resolver para **outro schema** (p. ex. `public.ingestionstatus`). Fixe o `search_path` no ROLE da app **e** qualifique tipos: `ai.ingestionstatus`. ([Stack Overflow](https://stackoverflow.com/questions/34098326/how-to-select-a-schema-in-postgres-when-using-psql?utm_source=chatgpt.com))

7. **Bindings tipados evitam `CAST(...)` manual**

* Em `text()`/SQL cru, use `bindparam(..., type_=Enum(...))` para o SQLAlchemy adaptar corretamente em vez de concatenar `::tipo`. ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/core/sqlelement.html?utm_source=chatgpt.com))

---

# **Padrão recomendável (modelo de código)**

**Enum Python** (grava *valores* minúsculos; tipo nativo no schema “ai”; criação segura via MetaData):

\# models.py  
from enum import Enum  
from sqlalchemy import Enum as SAEnum  
from sqlalchemy.orm import Mapped, mapped\_column, DeclarativeBase

class Base(DeclarativeBase):  
    pass

class IngestionStatus(str, Enum):  
    PENDING    \= "pending"  
    PROCESSING \= "processing"  
    SUCCEEDED  \= "succeeded"  
    FAILED     \= "failed"

StatusEnum \= SAEnum(  
    IngestionStatus,  
    name="ingestionstatus",  
    schema="ai",  
    metadata=Base.metadata,                     \# garante CREATE TYPE no create\_all()  
    values\_callable=lambda e: \[m.value for m in e\],  \# persiste "processing" etc.  
    native\_enum=True,  
    validate\_strings=True,  
)

class IngestionQueue(Base):  
    \_\_tablename\_\_ \= "ingestion\_queue"  
    \_\_table\_args\_\_ \= {"schema": "ai"}           \# tabela no schema ai  
    id: Mapped\[int\] \= mapped\_column(primary\_key=True)  
    status: Mapped\[IngestionStatus\] \= mapped\_column(StatusEnum, nullable=False)

Por que assim? O `metadata=` e o `schema=` no `Enum` eliminam a ambiguidade de onde o **TYPE** será criado; `values_callable` garante que o banco use os **valores** do Enum (minúsculos), compatíveis com suas queries. ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/core/type_basics.html))

Se você **preferir evitar TYPE nativo** (simplifica migrações, perde algumas garantias), use `native_enum=False` **e remova `CAST(... AS ai.ingestionstatus)`** de qualquer SQL cru (a coluna vira `VARCHAR` \+ CHECK). ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/orm/declarative_tables.html?utm_source=chatgpt.com))

---

# **Runbook de correção (seguro e reproduzível)**

Meta: sair do estado “tipo inexistente/incoerente” para um estado **coeso** com labels minúsculos e compatível com o código.

### **0\) Pausar o worker**

Pare o Celery para não reciclar pools/loops corrompidos durante a janela de migração.

### **1\) Inspecionar o estado atual**

Rode (somente leitura):

\-- Todos os ENUM homônimos (por schema) e seus labels  
SELECT n.nspname AS schema, t.typname, e.enumlabel, e.enumsortorder  
FROM pg\_type t  
JOIN pg\_enum e ON e.enumtypid \= t.oid  
JOIN pg\_namespace n ON n.oid \= t.typnamespace  
WHERE t.typname \= 'ingestionstatus'  
ORDER BY n.nspname, e.enumsortorder;

\-- search\_path efetivo  
SHOW search\_path;

\-- Labels do ai.ingestionstatus (se existir)  
SELECT enum\_range(NULL::ai.ingestionstatus);

([PostgreSQL](https://www.postgresql.org/docs/current/functions-enum.html?utm_source=chatgpt.com))

### **2\) Escolher a estratégia de migração**

**A. Só faltam labels** (ex.: não existe `'processing'` no `ai.ingestionstatus`):

Use DDL incremental **sem downtime**:

ALTER TYPE ai.ingestionstatus ADD VALUE IF NOT EXISTS 'processing' AFTER 'pending';  
\-- repita para outros labels necessários

([PostgreSQL](https://www.postgresql.org/docs/current/sql-altertype.html?utm_source=chatgpt.com))

**B. Precisa “corrigir” labels (maiúsculas → minúsculas) / reordenar / remover**:

Use a estratégia **v2 → trocar colunas → dropar antigo → renomear**:

BEGIN;

\-- 1\) Criar o novo tipo com o conjunto e ordem corretos  
CREATE TYPE ai.ingestionstatus\_v2 AS ENUM ('pending','processing','succeeded','failed');

\-- 2\) Migrar as colunas que usam o tipo antigo  
ALTER TABLE ai.ingestion\_queue  
  ALTER COLUMN status TYPE ai.ingestionstatus\_v2  
  USING status::text::ai.ingestionstatus\_v2;

\-- (migre demais tabelas que usem o tipo)

\-- 3\) Remover o tipo antigo e renomear o novo  
DROP TYPE ai.ingestionstatus;                   \-- só quando não houver mais dependências  
ALTER TYPE ai.ingestionstatus\_v2 RENAME TO ingestionstatus;

COMMIT;

Observações:  
 • **Não** use `CASCADE` em produção sem mapear todas dependências.  
 • Remoção/reordenação **exige** recriar o tipo (não há `DROP VALUE`). ([PostgreSQL](https://www.postgresql.org/docs/current/sql-droptype.html?utm_source=chatgpt.com))

### **3\) Fixar o modelo e as queries**

* Aplique o **modelo de código** acima (Enum com `metadata`, `schema`, `values_callable`). ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/core/type_basics.html))

Em SQL cru, **troque `::ai.ingestionstatus`** por **bind param tipado**:

 from sqlalchemy import text, bindparam  
stmt \= text("""  
    UPDATE ai.ingestion\_queue  
    SET status \= :new\_status  
    WHERE status \= :old\_status  
""").bindparams(  
    bindparam("new\_status", type\_=StatusEnum),  
    bindparam("old\_status", type\_=StatusEnum),  
)

*  Isso elimina dependência de `CAST`. ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/core/sqlelement.html?utm_source=chatgpt.com))

### **4\) Alembic (padrão industrial)**

* Para **adicionar** labels: `op.execute("ALTER TYPE ai.ingestionstatus ADD VALUE 'processing' AFTER 'pending'")`.

* Para **remover/reordenar**: faça a **v2 → migrate → drop → rename** dentro de uma revisão.

* Dica: em bancos grandes, `ADD VALUE` pode ter nuances transacionais; garanta que o uso do novo label só ocorra **após o commit** da revisão. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-altertype.html?utm_source=chatgpt.com))

### **5\) Sanity checks pós-migração**

SELECT enum\_range(NULL::ai.ingestionstatus);  \-- deve mostrar \['pending','processing','succeeded','failed'\]  
SELECT DISTINCT status FROM ai.ingestion\_queue ORDER BY 1;

([PostgreSQL](https://www.postgresql.org/docs/current/functions-enum.html?utm_source=chatgpt.com))

### **6\) Reiniciar o worker com blindagem assíncrona**

Se você usa `asyncio.run(...)` dentro do Celery, crie/feche **engine/session** dentro da corrotina e faça `await engine.dispose()` no `finally` (evita “loop zumbi” entre execuções). *(Boas práticas de pool/loop em tasks assíncronas.)*

---

# **Alternativa arquitetural (quando ENUM dói demais)**

Se o ciclo de vida dos status muda com frequência, considere **`native_enum=False`** (coluna `VARCHAR` \+ CHECK) para reduzir atrito de migração — mas **não** use `CAST(... AS ai.ingestionstatus)` nessas queries (não existe TYPE). É o trade-off clássico: **migrabilidade** vs **tipo nativo**. ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/orm/declarative_tables.html?utm_source=chatgpt.com))

---

## **TL;DR da solução**

1. **Padronize o modelo** com `Enum(..., name="ingestionstatus", schema="ai", metadata=Base.metadata, values_callable=...)`. ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/core/type_basics.html))

2. **Migre** o tipo atual com **Opção A** (ADD VALUE) ou **Opção B** (v2→rename) conforme seu caso. ([PostgreSQL](https://www.postgresql.org/docs/current/sql-altertype.html?utm_source=chatgpt.com))

3. **Remova `CAST` manual** e use **bind params tipados** no SQL cru. ([docs.sqlalchemy.org](https://docs.sqlalchemy.org/en/latest/core/sqlelement.html?utm_source=chatgpt.com))

4. **Fixe `search_path`** e/ou sempre **qualifique** `ai.ingestionstatus`. ([Stack Overflow](https://stackoverflow.com/questions/34098326/how-to-select-a-schema-in-postgres-when-using-psql?utm_source=chatgpt.com))

5. **Gerencie via Alembic** daqui para frente (DDL explícito para enums). ([PostgreSQL](https://www.postgresql.org/docs/current/sql-altertype.html?utm_source=chatgpt.com))

Se quiser, eu já te devolvo um **script Alembic** pronto para a sua árvore de estados (com v2→rename), e um **patch** no `models.py`/`tasks.py` aplicando `values_callable`, `metadata` e `bindparam`.

**Análise Arquitetural e Soluções Estratégicas para o Gerenciamento de Tipos ENUM em PostgreSQL com SQLAlchemy e Alembic**  
---

## **Seção 1: Análise Abrangente da Interação entre SQLAlchemy, Schemas e Tipos ENUM Nativos do PostgreSQL**

### **1.1. Introdução à Complexidade do Problema**

O erro UndefinedObjectError: type "ai.ingestionstatus" does not exist encontrado durante a execução do worker Celery não representa uma falha trivial de implementação, mas sim um sintoma de um desafio arquitetural mais profundo e sutil. A dificuldade reside na orquestração da DDL (Data Definition Language) ao interagir simultaneamente com três componentes complexos: tipos de dados definidos pelo usuário (como ENUM no PostgreSQL), schemas de banco de dados não-padrão (o schema ai) e um ORM (Object-Relational Mapper) como o SQLAlchemy, especialmente em um contexto assíncrono.

A experiência relatada não é um caso isolado. A combinação desses fatores é uma área notória por suas complexidades, e a pesquisa na comunidade de desenvolvimento corrobora a existência de desafios semelhantes, particularmente em ambientes que utilizam programação assíncrona. Relatos de erros como UndefinedObjectError e InternalServerError: cache lookup failed for type são encontrados em contextos que envolvem ORMs assíncronos, tipos ENUM e schemas, indicando que a orquestração de DDL nesses cenários é inerentemente frágil.1 Portanto, a análise deve transcender a busca por uma correção pontual e focar na causa raiz sistêmica do problema.

### **1.2. O Ciclo de Vida de um SchemaType no SQLAlchemy**

Para compreender a origem da falha, é crucial analisar como o SQLAlchemy gerencia os tipos de dados do banco de dados. O tipo sqlalchemy.dialects.postgresql.ENUM é uma implementação especializada de uma classe base mais genérica chamada SchemaType.3 Isso significa que, para o SQLAlchemy, um tipo ENUM não é apenas uma propriedade de uma coluna, mas um objeto de banco de dados de primeira classe, assim como uma Table. Como tal, ele possui seu próprio ciclo de vida e comandos DDL associados, nomeadamente CREATE TYPE e DROP TYPE.

A função MetaData.create\_all() é o mecanismo pelo qual o SQLAlchemy tenta traduzir a definição dos modelos Python para um schema de banco de dados.4 Ao ser invocada, essa função inspeciona todos os objetos Table e SchemaType registrados no objeto MetaData e tenta gerar e executar as DDLs em uma ordem que respeite suas dependências.

A dependência crítica neste caso é a ordem de criação. A sintaxe SQL para criar a tabela ai.ingestion\_queue depende da pré-existência do tipo ai.ingestionstatus. A sequência correta de comandos DDL deve ser:

1. CREATE SCHEMA IF NOT EXISTS ai;  
2. CREATE TYPE ai.ingestionstatus AS ENUM ('pending', 'processing',...);  
3. CREATE TABLE ai.ingestion\_queue (..., status ai.ingestionstatus,...);

O erro UndefinedObjectError é uma prova conclusiva de que esta ordem não está sendo respeitada. O sistema está tentando executar o passo 3 (CREATE TABLE) antes do passo 2 (CREATE TYPE), resultando em uma falha, pois o tipo de dados referenciado na definição da coluna ainda não existe no catálogo do banco de dados.

### **1.3. O Fator Agravante: Schemas e Contextos Assíncronos**

A decisão de utilizar um schema explícito (schema="ai"), embora seja uma excelente prática para a organização lógica do banco de dados, é o principal catalisador que expõe a fragilidade do mecanismo de resolução de dependências do create\_all. A presença do schema adiciona uma camada de complexidade. O SQLAlchemy precisa não apenas ordenar CREATE TYPE versus CREATE TABLE, mas também garantir que o próprio schema ai exista e seja o contexto correto para a criação do tipo.

Adicionalmente, o contexto assíncrono do worker Celery e do driver de banco de dados (provavelmente asyncpg) agrava o problema. A literatura técnica e os relatos de problemas em projetos de código aberto indicam que a orquestração de DDL através de um *event loop* pode ser menos robusta do que em um contexto síncrono tradicional.1 A complexidade do sistema de eventos do SQLAlchemy, que precisa gerenciar o estado da conexão e a execução de comandos de forma não-bloqueante, aumenta a probabilidade de ocorrerem condições de corrida ou falhas na ordenação das DDLs. A sugestão em um desses relatos de usar um SQLAlchemy não-assíncrono ou uma ferramenta como o Alembic para executar create\_all aponta diretamente para a instabilidade dessa operação em ambientes assíncronos.1

A combinação desses fatores leva a uma conclusão fundamental: o problema não reside em um erro de sintaxe no código da aplicação, mas em uma falha na orquestração de DDL pelo create\_all em um cenário que ultrapassa os limites de sua confiabilidade. A confiança em mecanismos de "criação mágica" como create\_all para cenários de produção com schemas customizados e tipos definidos pelo usuário revela-se um anti-padrão arquitetural. A solução duradoura não é tentar "consertar" o comportamento do create\_all com soluções paliativas, mas sim substituí-lo por um sistema de gerenciamento de schema explícito, versionado e determinístico.

---

## **Seção 2: Diagnóstico da Causa Raiz: As Limitações do metadata.create\_all em Ambientes Evolutivos**

### **2.1. create\_all: Uma Ferramenta de Bootstrap, Não de Migração**

A análise aprofundada do problema revela uma dissonância entre a ferramenta utilizada (create\_all) e o objetivo desejado (gerenciamento de um schema de banco de dados em evolução). A função MetaData.create\_all() foi projetada fundamentalmente como uma ferramenta de *bootstrap*. Seu propósito é inicializar um banco de dados a partir do zero, refletindo o estado atual dos modelos Python. Ela opera de forma inerentemente "sem estado" (*stateless*); ela não possui conhecimento de como o schema do banco de dados era antes de sua execução.

Essa característica a torna perfeitamente adequada para ambientes de teste, onde bancos de dados são criados e destruídos frequentemente, ou para a prototipagem inicial de uma aplicação. No entanto, ela é fundamentalmente inadequada para gerenciar o ciclo de vida de um banco de dados em produção. create\_all não pode, por exemplo, adicionar um novo valor a um tipo ENUM existente sem recriá-lo, o que falharia se o tipo já estivesse em uso. Ela não pode renomear uma coluna sem perder dados, adicionar uma constraint a uma tabela existente ou realizar qualquer outra alteração não-destrutiva que preserve os dados. O fluxo de trabalho de drop\_all/create\_all é viável apenas em desenvolvimento. O erro persistente com o ENUM é o primeiro sintoma de que a aplicação atingiu um nível de complexidade de schema que excede a capacidade dessa ferramenta.

### **2.2. O Comportamento de native\_enum=False: Uma Estratégia de Evasão**

A tentativa de utilizar o parâmetro native\_enum=False na definição da coluna Enum é um passo diagnóstico importante, pois revela a natureza do problema. A pesquisa confirma que esta opção instrui o SQLAlchemy a não criar um tipo ENUM nativo no PostgreSQL.5 Em vez disso, a estratégia padrão é criar uma coluna VARCHAR no banco de dados. Em versões mais antigas do SQLAlchemy, essa opção também gerava automaticamente uma CHECK constraint na tabela para garantir que apenas os valores definidos no Enum Python fossem inseridos.6 No entanto, a partir da versão 1.4, o comportamento padrão mudou, e o parâmetro create\_constraint agora é False por padrão, o que significa que, sem configuração adicional, a validação ocorreria apenas no lado da aplicação.3

A falha subsequente, um UndefinedObjectError, ao usar native\_enum=False é extremamente reveladora. Ela ocorreu porque o código do worker, que continha uma query SQL bruta (CAST(... AS ai.ingestionstatus)), ainda presumia a existência do tipo nativo ai.ingestionstatus. Isso demonstra um desacoplamento perigoso entre as camadas de abstração. A mudança na definição do modelo ORM (native\_enum=False) invalidou completamente a premissa da solução de baixo nível (o CAST em SQL).

Este padrão de falha expõe um desacoplamento de abstração. Foi feita uma tentativa de resolver um problema de alto nível (a falha de criação do ENUM pelo ORM) com uma solução de baixo nível (um CAST explícito em SQL). No entanto, uma alteração subsequente na abstração do ORM (native\_enum=False) tornou a solução de baixo nível inválida. A cadeia de eventos foi a seguinte:

1. O problema inicial foi a falha do create\_all em criar o tipo ENUM nativo na ordem correta.  
2. Uma tentativa de solução em SQL foi introduzida: CAST(:param AS ai.ingestionstatus), que pressupunha que o tipo ai.ingestionstatus deveria existir.  
3. Uma nova tentativa de solução foi aplicada no nível do ORM: native\_enum=False, que instruiu o SQLAlchemy a *não* criar o tipo ai.ingestionstatus.  
4. O resultado foi um conflito direto: a query SQL tentou usar um tipo que a definição do ORM agora garantia que não existiria, levando inevitavelmente ao UndefinedObjectError.

A lição fundamental é que a mistura de abstrações de ORM com SQL bruto, embora poderosa, é frágil e exige uma abordagem holística. Qualquer estratégia de solução de problemas deve considerar o impacto das mudanças em todas as camadas do sistema. O uso de native\_enum=False não consertou o problema do ENUM; ele apenas o transformou de um erro de *tipo de dados* para um erro de *integridade referencial*, mascarando a causa raiz, que é a inadequação do create\_all para a tarefa em questão.

---

## **Seção 3: A Solução Padrão da Indústria: Gerenciamento de Schema Declarativo com Alembic**

### **3.1. Introdução ao Alembic**

A solução canônica para o gerenciamento de schemas de banco de dados no ecossistema SQLAlchemy é o Alembic.7 O Alembic é uma ferramenta de migração de banco de dados que opera sob o princípio do controle de versão. Ele pode ser conceituado como um "Git para o seu banco de dados", permitindo que as alterações no schema sejam tratadas como código: versionadas, revisadas, repetíveis e aplicadas de forma incremental e controlada. Ele preenche a lacuna deixada pelo create\_all, fornecendo um mecanismo robusto para a evolução de um schema de banco de dados ao longo do tempo, sem a necessidade de destruir e recriar dados.

### **3.2. Abordagem Imperativa (create\_all) vs. Migração Versionada (Alembic)**

É fundamental contrastar as duas filosofias de gerenciamento de schema. A abordagem do create\_all é **imperativa**: ela instrui o sistema a "fazer o banco de dados parecer com este estado dos modelos Python, agora". Ela não tem memória do estado anterior e sua lógica de ordenação de DDL é implícita e, como visto, frágil em casos complexos.

A abordagem do Alembic é **declarativa e baseada em estado**: ela funciona gerando scripts de migração que contêm as instruções explícitas para transicionar o schema de uma versão para a próxima. Cada migração é um script Python que define uma função upgrade() e uma downgrade(), contendo as operações DDL necessárias para aplicar ou reverter a mudança.

Essa abordagem resolve o problema de ordenação de DDL de forma definitiva. O desenvolvedor tem controle total e explícito sobre a ordem das operações dentro de um script de migração. Se um tipo ENUM precisa ser criado antes de uma tabela, o script de migração conterá a chamada para criar o tipo (op.execute('CREATE TYPE...') ou usando um construtor de tipo do Alembic) seguida pela chamada para criar a tabela (op.create\_table(...)). Essa explicitude elimina a ambiguidade e a fragilidade do mecanismo implícito do create\_all.

### **3.3. O Fluxo de Trabalho do Alembic**

A adoção do Alembic introduz um fluxo de trabalho estruturado e confiável para todas as alterações de schema:

1. **Inicialização (alembic init)**: Este comando é executado uma única vez para criar o diretório de migrações (alembic/) e o arquivo de configuração (alembic.ini).  
2. **Geração de Revisão (alembic revision \--autogenerate \-m "mensagem")**: Este é o passo central. O Alembic se conecta ao banco de dados, lê o estado atual do schema (armazenado na tabela alembic\_version), compara-o com a definição dos modelos SQLAlchemy na aplicação e gera automaticamente um script de migração Python contendo as diferenças detectadas.  
3. **Aplicação da Migração (alembic upgrade head)**: Este comando aplica todas as migrações pendentes, atualizando o schema do banco de dados para a versão mais recente e registrando a nova versão na tabela alembic\_version.

É importante notar que, embora a funcionalidade autogenerate seja extremamente poderosa, ela não é infalível. Para operações complexas, como a alteração de um tipo ENUM (adicionar ou remover valores), o Alembic padrão pode gerar um script vazio ou incorreto, exigindo intervenção manual.7 Este é precisamente o problema que ferramentas de extensão, a serem discutidas na próxima seção, se propõem a resolver.

A adoção do Alembic representa uma mudança de paradigma fundamental: de um gerenciamento de schema implícito e propenso a erros para um gerenciamento explícito, versionado e robusto. O problema do ENUM não é um caso isolado; qualquer alteração de schema futura, como adicionar uma coluna NOT NULL a uma tabela populada, teria encontrado as mesmas limitações intransponíveis do create\_all. O ENUM foi apenas o primeiro sintoma de uma inadequação arquitetural mais profunda. Ao adotar o Alembic, a solução não apenas corrige o problema atual, mas também prepara o projeto para qualquer evolução futura do schema, estabelecendo uma prática de engenharia de software sólida e escalável. A integração de uma ferramenta de migração deve ser considerada uma prática padrão não-negociável para qualquer projeto SQLAlchemy destinado à produção, tão essencial quanto o controle de versão para o código-fonte.

---

## **Seção 4: Automação Avançada de Migrações de ENUM: Uma Análise da alembic-postgresql-enum**

### **4.1. Apresentação da Biblioteca**

A complexidade do gerenciamento do ciclo de vida dos tipos ENUM no PostgreSQL é um problema tão comum e desafiador que motivou a criação de soluções especializadas pela comunidade. A biblioteca alembic-postgresql-enum é uma extensão para o Alembic projetada especificamente para preencher uma lacuna crítica em sua funcionalidade de autogenerate: o tratamento correto e automatizado de ENUMs nativos do PostgreSQL.12 A própria existência desta biblioteca serve como prova definitiva de que o problema enfrentado não é trivial e justifica o uso de uma ferramenta dedicada. Ela transforma o que seria um processo manual, complexo e propenso a erros em uma operação automatizada e segura.

### **4.2. Integração e Funcionalidades**

Uma das grandes vantagens da alembic-postgresql-enum é sua simplicidade de integração. O processo consiste em dois passos:

1. Instalar a biblioteca: pip install alembic-postgresql-enum.  
2. Adicionar uma única linha de importação no topo do arquivo de configuração do Alembic: import alembic\_postgresql\_enum em migrations/env.py.12

Uma vez integrada, a biblioteca aprimora o comando alembic revision \--autogenerate para detectar e gerenciar automaticamente todo o ciclo de vida dos ENUMs:

* **Criação de Tipos**: A biblioteca detecta a definição de um novo ENUM nos modelos SQLAlchemy e gera a DDL CREATE TYPE necessária na migração. Crucialmente, ela garante que esta operação ocorra *antes* da criação de qualquer tabela que dependa desse tipo, resolvendo diretamente o problema de ordenação que causou o UndefinedObjectError original.12  
* **Sincronização de Valores**: Esta é a sua funcionalidade mais poderosa. A biblioteca compara os valores definidos no enum.Enum do Python com os rótulos existentes no tipo ENUM do banco de dados. Se valores forem adicionados ou removidos, ela gera automaticamente uma chamada para a função op.sync\_enum\_values. Esta função encapsula a lógica DDL correta, seja um simples ALTER TYPE... ADD VALUE para adições, ou a sequência complexa e perigosa de comandos necessários para remover um valor de forma segura.12  
* **Remoção de Tipos**: Se um tipo ENUM definido no banco de dados não for mais referenciado por nenhum modelo SQLAlchemy, a biblioteca detectará que ele se tornou órfão e gerará o comando DROP TYPE correspondente na migração.12

De forma fundamental para o problema em questão, a biblioteca foi projetada para suportar schemas. As funções geradas, como op.sync\_enum\_values, incluem parâmetros explícitos como enum\_schema e table\_schema, garantindo que as operações DDL sejam direcionadas ao schema correto (ai), eliminando qualquer ambiguidade.13

### **4.3. Exemplo Prático de Migração**

O impacto da biblioteca no fluxo de trabalho é transformador. Considere um cenário onde um novo status, 'archived', é adicionado ao Enum IngestionStatus.

* **Antes (Alembic Padrão)**: Executar alembic revision \--autogenerate provavelmente resultaria em um script de migração vazio. O desenvolvedor teria que pesquisar a sintaxe correta do ALTER TYPE, adicioná-la manualmente ao script de migração e garantir que ela fosse executada dentro de um bloco de transação apropriado, um processo manual e sujeito a erros.10  
* **Depois (alembic-postgresql-enum)**: Com a biblioteca instalada, o mesmo comando alembic revision \--autogenerate produziria um script de migração contendo uma chamada gerada automaticamente, semelhante a esta:  
* Python

\# \#\#\# commands auto generated by Alembic \- please adjust\! \#\#\#  
op.sync\_enum\_values(  
    'ai',  
    'ingestionstatus',  
    \['pending', 'processing', 'completed', 'failed', 'archived'\],  
   ,  
    enum\_values\_to\_rename=  
)  
\# \#\#\# end Alembic commands \#\#\#

*   
* Este código é declarativo, legível e, o mais importante, correto e seguro.

A complexidade das operações DDL para ENUMs no PostgreSQL, especialmente a remoção de valores, é a principal razão de ser desta biblioteca. A documentação do PostgreSQL e diversos artigos técnicos detalham o processo de múltiplos passos para remover um valor: ALTER TYPE RENAME TO...\_old, CREATE TYPE... (com os novos valores), ALTER TABLE... ALTER COLUMN... TYPE... USING...::text::..., e DROP TYPE...\_old.15 Executar esta sequência manualmente em uma migração é extremamente arriscado; um único erro pode levar à perda de dados ou a um estado de schema inconsistente. A alembic-postgresql-enum encapsula essa lógica perigosa em uma abstração testada e confiável. Adotar ferramentas especializadas do ecossistema como esta é uma marca de maturidade em engenharia de software, preferindo alavancar soluções robustas da comunidade em vez de implementar procedimentos manuais arriscados.

---

## **Seção 5: Análise Comparativa de Estratégias Alternativas: ENUM Nativo vs. VARCHAR com CHECK Constraint**

### **5.1. Duas Filosofias de Design**

A decisão de como modelar um conjunto restrito de valores em um banco de dados envolve um trade-off entre duas filosofias de design distintas. A escolha impacta não apenas a performance e o armazenamento, mas, de forma mais crítica, a complexidade operacional e a flexibilidade do sistema a longo prazo.

* **ENUM Nativo**: Esta abordagem prioriza a semântica do banco de dados, a segurança de tipo e a eficiência. O próprio tipo de dados (ENUM) é a fonte da verdade e da integridade. O banco de dados entende que a coluna contém um valor de um conjunto ordenado e estático, o que pode permitir otimizações internas.  
* **VARCHAR com CHECK Constraint**: Esta abordagem prioriza a flexibilidade operacional e a simplicidade da migração. A coluna é um tipo de dados padrão (VARCHAR), e a integridade é imposta por uma regra adicional (a CHECK constraint). Isso desacopla o tipo de dados da regra de validação, o que tem implicações significativas na evolução do schema.16

### **5.2. Tabela Comparativa Detalhada**

Para facilitar uma decisão arquitetural informada, a tabela a seguir sintetiza as principais diferenças entre as duas estratégias, com base em critérios de armazenamento, performance, segurança e, crucialmente, a complexidade da evolução do schema.

| Característica | ENUM Nativo do PostgreSQL | VARCHAR com CHECK Constraint | Análise e Recomendações |
| :---- | :---- | :---- | :---- |
| **Eficiência de Armazenamento** | **Alta.** Armazena um valor inteiro de 4 bytes por linha, que atua como um ponteiro para os rótulos de string armazenados centralmente no catálogo do sistema.17 | **Menor.** Armazena a string completa do valor em cada linha, mais uma sobrecarga de 1 ou 4 bytes. O consumo de espaço é proporcional ao comprimento médio das strings.18 | **ENUM vence.** A economia de espaço é significativa para tabelas com um número muito grande de linhas (centenas de milhões ou mais) ou quando os rótulos do enum são longos. Para a maioria das aplicações, a diferença pode ser negligenciável. |
| **Performance de Consulta** | **Potencialmente maior.** Comparações, ordenações e junções podem ser mais rápidas, pois o banco de dados pode operar nos valores inteiros internos em vez de realizar comparações de strings.19 | **Potencialmente menor.** Comparações de strings são computacionalmente mais caras do que comparações de inteiros. No entanto, com indexação adequada, a diferença de performance em consultas do mundo real é frequentemente marginal.19 | **ENUM tem uma leve vantagem teórica.** A menos que a coluna seja o principal gargalo de performance em consultas de altíssimo volume, a diferença provavelmente não será um fator decisivo. |
| **Segurança de Tipo (Type Safety)** | **Muito Alta.** O PostgreSQL impõe a segurança de tipo no nível do sistema. Não é possível, por exemplo, comparar acidentalmente um valor de mood\_enum com um valor de status\_enum, mesmo que seus rótulos de string sejam idênticos.18 | **Alta.** A CHECK constraint garante a integridade dos dados no banco de dados, rejeitando qualquer valor que não esteja na lista permitida. No entanto, a coluna ainda é do tipo TEXT/VARCHAR, então a segurança de tipo semântica é menor.16 | **Empate funcional para integridade de dados.** Ambas as abordagens previnem dados inválidos. A abordagem ENUM é semanticamente mais "pura" e oferece garantias de tipo mais fortes no nível do SQL. |
| **Evolução (Adicionar Valor)** | **Simples.** A adição de um novo valor é uma operação de primeira classe via ALTER TYPE... ADD VALUE. É uma operação rápida e não-bloqueante, embora deva ser executada fora de um bloco de transação explícito em algumas versões do PostgreSQL para ser utilizável imediatamente.10 | **Complexo.** Requer a remoção da constraint antiga e a adição de uma nova com a lista de valores atualizada. Se não for feita com cuidado, a operação ADD CONSTRAINT pode exigir um ACCESS EXCLUSIVE LOCK para validar todos os dados existentes.18 | **ENUM vence.** O processo para adicionar valores é significativamente mais simples e seguro. |
| **Evolução (Remover/Renomear Valor)** | **Muito Complexo e Perigoso.** O PostgreSQL não oferece um comando ALTER TYPE... DROP VALUE. A remoção de um valor exige uma migração complexa que envolve renomear o tipo antigo, criar um novo tipo com os valores corretos, alterar a coluna da tabela para usar o novo tipo (migrando os dados) e, finalmente, remover o tipo antigo. A etapa ALTER TABLE adquire um ACCESS EXCLUSIVE LOCK, que bloqueia todas as leituras e escritas na tabela, podendo causar downtime significativo.18 | **Gerenciável.** A remoção de um valor pode ser gerenciada com mais segurança. O processo envolve uma migração de dados para tratar as linhas que usam o valor obsoleto, seguida pela atualização da CHECK constraint. A atualização da constraint pode ser feita usando a técnica NOT VALID/VALIDATE CONSTRAINT, que minimiza o tempo de bloqueio e permite operações concorrentes na tabela.18 | **VARCHAR \+ CHECK vence categoricamente.** Esta é a principal e mais convincente razão para escolher esta abordagem em sistemas de alta disponibilidade que não podem tolerar longos bloqueios de tabela durante as migrações. |
| **Portabilidade entre BDs** | **Baixa.** A sintaxe e o comportamento dos tipos ENUM são altamente específicos do fornecedor (PostgreSQL vs. MySQL, por exemplo). O MS SQL Server nem sequer suporta ENUMs nativos.20 | **Alta.** VARCHAR e CHECK constraints são parte do padrão SQL e são suportados de forma mais consistente pela maioria dos sistemas de banco de dados relacionais. | **VARCHAR \+ CHECK vence.** Esta é a escolha preferível se houver qualquer possibilidade de que a aplicação precise suportar um banco de dados diferente no futuro. |

### **5.3. A Alternativa sqlalchemy-utils.ChoiceType**

Para desenvolvedores que optam pela abordagem VARCHAR \+ CHECK, a biblioteca sqlalchemy-utils oferece uma abstração conveniente chamada ChoiceType.21 Este tipo de coluna do SQLAlchemy automatiza o padrão de mapear um enum.Enum Python para uma coluna de banco de dados (que pode ser VARCHAR ou INTEGER). Ele lida com a coerção de tipos entre o objeto Enum da aplicação e sua representação no banco de dados, simplificando o código do modelo.23 No entanto, é importante notar que o ChoiceType por si só não gerencia a CHECK constraint no banco de dados; a criação e o gerenciamento da constraint ainda seriam responsabilidade do sistema de migração (Alembic).

---

## **Seção 6: O Papel do search\_path e as Melhores Práticas para Qualificação de Schema**

### **6.1. Entendendo o search\_path do PostgreSQL**

O search\_path é uma variável de configuração de sessão no PostgreSQL que define uma lista ordenada de schemas a serem pesquisados quando um objeto de banco de dados (como uma tabela, tipo ou função) é referenciado sem uma qualificação de schema explícita. Por padrão, o search\_path é geralmente configurado como "$user", public, o que significa que o PostgreSQL primeiro procurará por um schema com o mesmo nome do usuário da sessão e, em seguida, procurará no schema public.24 Se um objeto não for encontrado em nenhum schema do search\_path, o PostgreSQL retorna um erro, mesmo que o objeto exista em outro schema do banco de dados.

### **6.2. Por Que Manipular o search\_path é um Anti-Padrão com Alembic**

Embora possa parecer tentador "consertar" o problema de UndefinedObjectError simplesmente adicionando o schema ai ao search\_path da conexão (SET search\_path TO ai, public), esta é uma solução frágil e considerada um anti-padrão em aplicações modernas que utilizam ferramentas de migração.

A pesquisa e a documentação da comunidade SQLAlchemy/Alembic são inequívocas neste ponto: a funcionalidade autogenerate do Alembic **"se confunde completamente"** (completely messes up) quando o search\_path é utilizado para controle de schema.25 O Alembic precisa de uma visão clara e inequívoca do estado do banco de dados para compará-lo com os modelos da aplicação. Quando o search\_path é alterado, o Alembic pode não conseguir determinar corretamente em qual schema um objeto existe ou deveria ser criado/alterado, levando à geração de scripts de migração incorretos ou, pior, à falha em detectar mudanças necessárias.

Além da incompatibilidade com o Alembic, a manipulação do search\_path introduz outras complexidades. Por exemplo, um ROLLBACK de transação no PostgreSQL também reverte qualquer comando SET search\_path executado dentro dessa transação, o que pode levar a um comportamento imprevisível e difícil de depurar, onde comandos subsequentes na mesma sessão são executados contra o schema errado.25

### **6.3. A Prática Recomendada: Qualificação Explícita e Consistente**

Este diagnóstico aponta para um princípio fundamental de design de software robusto, ecoado no Zen do Python: "Explícito é melhor que implícito". A dependência de um search\_path implícito cria um acoplamento oculto e frágil entre a lógica da aplicação e a configuração da sessão do banco de dados.

A única abordagem verdadeiramente robusta e confiável é a **qualificação explícita e consistente do schema** em todas as camadas da aplicação:

* **Modelos SQLAlchemy**: Todas as definições de tabela devem incluir explicitamente o schema, seja através do argumento schema='ai' no construtor Table ou, mais comumente em modelos declarativos, usando \_\_table\_args\_\_ \= {'schema': 'ai'}. Da mesma forma, tipos SchemaType como ENUM devem ser definidos com Enum(..., schema='ai').  
* **Migrações Alembic**: Os scripts de migração gerados pelo Alembic devem referenciar o schema explicitamente em todas as operações, como op.create\_table('minha\_tabela',..., schema='ai'). Ferramentas como alembic-postgresql-enum já seguem esta prática.  
* **Queries Manuais/SQL Bruto**: Todas as queries SQL escritas manualmente no código da aplicação (como no worker Celery) devem qualificar completamente os nomes dos objetos, por exemplo, SELECT \* FROM ai.ingestion\_queue e CAST(? AS ai.ingestionstatus).

Ao adotar a qualificação explícita, a aplicação se torna agnóstica à configuração do search\_path da conexão. Isso elimina a ambiguidade, torna o sistema mais previsível, mais fácil de depurar e garante que tanto a aplicação em tempo de execução quanto as ferramentas de migração offline (Alembic) compartilhem uma visão idêntica e correta do schema do banco de dados. A configuração do search\_path deve ser relegada ao seu propósito original: uma conveniência para o uso interativo do psql, e não uma ferramenta de namespace para a aplicação.

---

## **Seção 7: Plano de Ação e Recomendações Estratégicas**

Esta seção final fornece um guia prescritivo e passo a passo para refatorar a aplicação, aplicando o conhecimento adquirido nas seções anteriores para resolver o problema atual e estabelecer uma base arquitetural sólida para o futuro.

### **7.1. Passo 1: Integração do Alembic e alembic-postgresql-enum**

O primeiro passo é introduzir as ferramentas corretas para o gerenciamento de schema.

1. Adicione alembic e alembic-postgresql-enum às dependências do projeto (ex: requirements.txt ou pyproject.toml).  
2. Na raiz do projeto, execute o comando alembic init alembic para criar o diretório de migrações e o arquivo de configuração alembic.ini.  
3. Edite o arquivo alembic/env.py:  
   * No topo do arquivo, adicione import alembic\_postgresql\_enum.  
   * Localize a linha target\_metadata \= None. Importe o objeto Base dos seus modelos (from core.models import Base) e configure target\_metadata \= Base.metadata.  
   * Garanta que a configuração da URL do banco de dados no alembic.ini ou em env.py aponte para o banco de dados de desenvolvimento.

### **7.2. Passo 2: Limpeza e Geração da Migração de Base (Baseline)**

Para garantir um começo limpo, é necessário estabelecer uma migração inicial que represente o estado completo do schema atual.

1. Conecte-se ao banco de dados de desenvolvimento e execute um comando de limpeza final e completo: DROP SCHEMA ai CASCADE;.  
2. Execute o comando alembic revision \--autogenerate \-m "Initial schema baseline". Como o banco de dados está vazio, o Alembic irá comparar os modelos SQLAlchemy com um banco de dados vazio e gerar um script de migração para criar todo o schema do zero.

### **7.3. Passo 3: Revisão e Validação da Migração Gerada**

A automação é poderosa, mas a verificação humana é crucial.

1. Abra o arquivo de migração recém-criado em alembic/versions/.  
2. Inspecione cuidadosamente o código gerado na função upgrade(). Verifique se ele contém:  
   * A criação explícita do tipo ENUM no schema ai. Graças à alembic-postgresql-enum, isso deve ser tratado corretamente.  
   * A criação da tabela ingestion\_queue com a qualificação schema='ai'.  
   * A definição da coluna status referenciando corretamente o tipo ENUM recém-criado.  
3. Verifique novamente todos os modelos SQLAlchemy (core/models.py) e confirme que a qualificação de schema (schema="ai") está definida explicitamente para todas as tabelas e tipos ENUM.

### **7.4. Passo 4: Aplicação da Migração e Teste**

Com a migração validada, o próximo passo é construir o schema usando o Alembic.

1. Execute alembic upgrade head. Este comando aplicará a migração de base, criando o schema, o tipo e a tabela na ordem correta.  
2. Use uma ferramenta de banco de dados (DBeaver, psql) para inspecionar o banco de dados. Confirme que o tipo ai.ingestionstatus e a tabela ai.ingestion\_queue foram criados corretamente, com os rótulos do ENUM em minúsculas, conforme definido no código Python.  
3. Execute novamente o worker Celery e os testes relacionados. O UndefinedObjectError original deve ser permanentemente resolvido.

### **7.5. Passo 5: Refatoração para o Futuro**

Para consolidar a nova arquitetura, é essencial remover os mecanismos antigos e adotar o novo fluxo de trabalho.

1. Elimine completamente o script init\_db.py e qualquer chamada a Base.metadata.create\_all() ou drop\_all() do código da aplicação. O Alembic é agora a única fonte de verdade e o único mecanismo para alterações de schema.  
2. Institucionalize o fluxo de trabalho do Alembic para todas as futuras alterações de schema:  
   a. Modifique um modelo SQLAlchemy (ex: adicionar uma nova coluna).  
   b. Execute alembic revision \--autogenerate \-m "Descrição da mudança".  
   c. Revise e, se necessário, ajuste o script de migração gerado.  
   d. Execute alembic upgrade head para aplicar a mudança no banco de dados.

### **7.6. Recomendação Estratégica Final**

Com o problema imediato resolvido, uma decisão arquitetural de longo prazo deve ser considerada.

* **Para o problema atual**, a combinação de Alembic e alembic-postgresql-enum é uma solução perfeitamente robusta e confiável que permite continuar utilizando ENUMs nativos do PostgreSQL de forma segura e gerenciável. Se as alterações nos valores do IngestionStatus são raras, esta é uma excelente solução.  
* **Para o futuro**, especialmente se a aplicação exigir alta disponibilidade (minimizar downtime de implantação) e se espera que os conjuntos de valores restritos mudem com frequência, é **fortemente recomendado considerar a estratégia de VARCHAR com CHECK constraint** para novos modelos. Como detalhado na Seção 5, a flexibilidade operacional desta abordagem, particularmente no que diz respeito à remoção de valores sem a necessidade de bloqueios de tabela exclusivos e prolongados, oferece uma vantagem significativa em ambientes de produção dinâmicos.

A escolha final entre as duas estratégias dependerá dos requisitos operacionais específicos do projeto. A infraestrutura agora está preparada para suportar qualquer uma das duas abordagens de forma robusta e escalável.

