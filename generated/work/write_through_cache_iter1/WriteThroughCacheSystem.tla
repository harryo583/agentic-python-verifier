---- MODULE WriteThroughCacheSystem ----
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Keys, Vals, Missing

VARIABLES store, cache, lastReadValid, lastReadKey, lastReadVal

S == INSTANCE BackingStore_Impl WITH Keys <- Keys, Vals <- Vals, Missing <- Missing, store <- store
C == INSTANCE Cache_Impl WITH Keys <- Keys, Vals <- Vals, Missing <- Missing, store <- store, cache <- cache, lastReadValid <- lastReadValid, lastReadKey <- lastReadKey, lastReadVal <- lastReadVal

vars == <<store, cache, lastReadValid, lastReadKey, lastReadVal>>

Init == S!Init /\ C!Init
Next == S!Next \/ C!Next
Spec == Init /\ [][Next]_vars

CacheAgrees ==
  \A k \in Keys : (cache[k] # Missing) => (cache[k] = store[k])

StoreWellFormed ==
  /\ DOMAIN store = Keys
  /\ \A k \in Keys : store[k] \in (Vals \cup {Missing})

CacheWellFormed ==
  /\ DOMAIN cache = Keys
  /\ \A k \in Keys : cache[k] \in (Vals \cup {Missing})

LastReadConsistent ==
  lastReadValid => /\ lastReadKey \in Keys
                   /\ lastReadVal \in (Vals \cup {Missing})
                   /\ lastReadVal = store[lastReadKey]

Inv ==
  /\ StoreWellFormed
  /\ CacheWellFormed
  /\ CacheAgrees
  /\ LastReadConsistent

Property ==
  /\ CacheAgrees
  /\ LastReadConsistent

====
