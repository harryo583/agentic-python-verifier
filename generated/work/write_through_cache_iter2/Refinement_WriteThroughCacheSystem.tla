---- MODULE Refinement_WriteThroughCacheSystem ----
EXTENDS WriteThroughCacheSystem

Abs_BackingStore == INSTANCE BackingStore_Abs WITH
    storePresent <- S!storePresent,
    storeVal <- S!storeVal

Abs_Cache == INSTANCE Cache_Abs WITH
    storePresent <- C!storePresent,
    storeVal <- C!storeVal,
    cachePresent <- C!cachePresent,
    cacheVal <- C!cacheVal,
    lastReadValid <- C!lastReadValid,
    lastReadKey <- C!lastReadKey,
    lastReadVal <- C!lastReadVal

RefinementSpec == /\ Abs_BackingStore!Spec
                  /\ Abs_Cache!Spec

====
