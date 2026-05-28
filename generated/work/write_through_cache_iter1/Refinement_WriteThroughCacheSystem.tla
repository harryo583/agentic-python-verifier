---- MODULE Refinement_WriteThroughCacheSystem ----
EXTENDS WriteThroughCacheSystem

Abs_BackingStore == INSTANCE BackingStore_Abs WITH store <- S!store

Abs_Cache == INSTANCE Cache_Abs WITH
    store <- C!store,
    cache <- C!cache,
    lastReadValid <- C!lastReadValid,
    lastReadKey <- C!lastReadKey,
    lastReadVal <- C!lastReadVal

RefinementSpec == /\ Abs_BackingStore!Spec
                  /\ Abs_Cache!Spec

====
