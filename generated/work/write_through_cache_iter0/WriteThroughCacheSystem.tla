---- MODULE WriteThroughCacheSystem ----
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Keys, Vals, Missing

VARIABLES store, cache, lastRead

S == INSTANCE BackingStore_Impl WITH Keys <- Keys, Vals <- Vals, Missing <- Missing, store <- store
C == INSTANCE Cache_Impl WITH Keys <- Keys, Vals <- Vals, Missing <- Missing, store <- store, cache <- cache, lastRead <- lastRead

vars == <<store, cache, lastRead>>

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
  \/ lastRead = Missing
  \/ /\ lastRead.key \in Keys
     /\ lastRead.val \in (Vals \cup {Missing})
     /\ lastRead.val = store[lastRead.key]

Inv ==
  /\ StoreWellFormed
  /\ CacheWellFormed
  /\ CacheAgrees
  /\ LastReadConsistent

Property ==
  /\ CacheAgrees
  /\ LastReadConsistent

====
