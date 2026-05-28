---- MODULE WriteThroughCacheSystem ----
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Keys, Vals, Missing

VARIABLES store, cache

S == INSTANCE BackingStore_Impl WITH store <- store
C == INSTANCE FrontCache_Impl WITH cache <- cache

vars == <<store, cache>>

Init == S!Init /\ C!Init
Next == S!Next /\ C!Next
Spec == Init /\ [][Next]_vars

StoreOK ==
  /\ DOMAIN store \subseteq Keys
  /\ \A k \in DOMAIN store : store[k] \in Vals

CacheOK ==
  /\ DOMAIN cache \subseteq Keys
  /\ \A k \in DOMAIN cache : cache[k] \in Vals

CacheAgreement ==
  \A k \in DOMAIN cache :
    /\ k \in DOMAIN store
    /\ cache[k] = store[k]

Inv ==
  /\ StoreOK
  /\ CacheOK
  /\ CacheAgreement

Property == CacheAgreement

====
