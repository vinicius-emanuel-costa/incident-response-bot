<b>1. Diagnostico</b>
<code>-- PostgreSQL: queries ativas
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC;</code>

<b>2. Identificar queries lentas</b>
- Verificar slow query log
- Checar locks: <code>SELECT * FROM pg_locks WHERE NOT granted;</code>
- Conexoes ativas vs max_connections

<b>3. Acoes imediatas</b>
- Matar query travada: <code>SELECT pg_terminate_backend(pid);</code>
- Se ha lock: identificar e resolver deadlock
- Verificar replicacao (lag)

<b>4. Otimizacao</b>
- EXPLAIN ANALYZE na query problematica
- Verificar indices faltantes
- Checar vacuum/analyze recentes

<b>5. Mitigacao</b>
- Adicionar read replicas para queries de leitura
- Implementar connection pooling (PgBouncer)
- Cache de queries frequentes (Redis)

<b>6. Prevencao</b>
- Monitorar pg_stat_statements
- Alertas de replication lag > 30s
- Review de queries em PRs
- Maintenance window para vacuum/reindex
