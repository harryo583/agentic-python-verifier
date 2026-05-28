---- MODULE WriteThroughCacheSystem ----
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Keys, Vals

VARIABLES storePresent, storeVal, cachePresent, cacheVal, lastReadValid, lastReadKey, lastReadVal

S == INSTANCE BackingStore_Impl WITH Keys <- Keys, Vals <- Vals, storePresent <- storePresent, storeVal <- storeVal
C == INSTANCE Cache_Impl WITH Keys <- Keys, Vals <- Vals, storePresent <- storePresent, storeVal <- storeVal, cachePresent <- cachePresent, cacheVal <- cacheVal, lastReadValid <- lastReadValid, lastReadKey <- lastReadKey, lastReadVal <- lastReadVal

vars == <<storePresent, storeVal, cachePresent, cacheVal, lastReadValid, lastReadKey, lastReadVal>>

Init == S!Init /\ C!Init
Next == S!Next \/ C!Next
Spec == Init /\ [][Next]_vars

StoreWellFormed ==
  /\ DOMAIN storePresent = Keys
  /\ DOMAIN storeVal = Keys
  /\ \A k \in Keys : storePresent[k] \in BOOLEAN
  /\ \A k \in Keys : storeVal[k] \in Vals

CacheWellFormed ==
  /\ DOMAIN cachePresent = Keys
  /\ DOMAIN cacheVal = Keys
  /\ \A k \in Keys : cachePresent[k] \in BOOLEAN
  /\ \A k \in Keys : cacheVal[k] \in Vals

CacheAgrees ==
  \A k \in Keys : cachePresent[k] =>
     /\ storePresent[k]
     /\ cacheVal[k] = storeVal[k]

LastReadConsistent ==
  lastReadValid =>
    /\ lastReadKey \in Keys
    /\ lastReadVal \in Vals
    /\ storePresent[lastReadKey]
    /\ lastReadVal = storeVal[lastReadKey]

Inv ==
  /\ StoreWellFormed
  /\ CacheWellFormed
  /\ CacheAgrees
  /\ LastReadConsistent

Property ==
  /\ CacheAgrees
  /\ LastReadConsistent

====
