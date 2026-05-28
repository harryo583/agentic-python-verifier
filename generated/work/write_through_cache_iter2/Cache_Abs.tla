---- MODULE Cache_Abs ----
EXTENDS Naturals

CONSTANTS Keys, Vals

VARIABLES storePresent, storeVal, cachePresent, cacheVal, lastReadValid, lastReadKey, lastReadVal

vars == <<storePresent, storeVal, cachePresent, cacheVal, lastReadValid, lastReadKey, lastReadVal>>

Zero == CHOOSE v \in Vals : \A w \in Vals : v <= w
SomeKey == CHOOSE k \in Keys : TRUE

Init ==
  /\ storePresent = [k \in Keys |-> FALSE]
  /\ storeVal = [k \in Keys |-> Zero]
  /\ cachePresent = [k \in Keys |-> FALSE]
  /\ cacheVal = [k \in Keys |-> Zero]
  /\ lastReadValid = FALSE
  /\ lastReadKey = SomeKey
  /\ lastReadVal = Zero

CacheWrite(k, v) ==
  /\ k \in Keys
  /\ v \in Vals
  /\ cachePresent' = [cachePresent EXCEPT ![k] = TRUE]
  /\ cacheVal' = [cacheVal EXCEPT ![k] = v]
  /\ storePresent' = [storePresent EXCEPT ![k] = TRUE]
  /\ storeVal' = [storeVal EXCEPT ![k] = v]
  /\ lastReadValid' = FALSE
  /\ lastReadKey' = lastReadKey
  /\ lastReadVal' = Zero

CacheReadHit(k) ==
  /\ k \in Keys
  /\ cachePresent[k]
  /\ lastReadValid' = TRUE
  /\ lastReadKey' = k
  /\ lastReadVal' = cacheVal[k]
  /\ UNCHANGED <<storePresent, storeVal, cachePresent, cacheVal>>

CacheReadMiss(k) ==
  /\ k \in Keys
  /\ ~cachePresent[k]
  /\ storePresent[k]
  /\ cachePresent' = [cachePresent EXCEPT ![k] = TRUE]
  /\ cacheVal' = [cacheVal EXCEPT ![k] = storeVal[k]]
  /\ lastReadValid' = TRUE
  /\ lastReadKey' = k
  /\ lastReadVal' = storeVal[k]
  /\ UNCHANGED <<storePresent, storeVal>>

CacheReadAbsent(k) ==
  /\ k \in Keys
  /\ ~cachePresent[k]
  /\ ~storePresent[k]
  /\ lastReadValid' = FALSE
  /\ lastReadKey' = k
  /\ lastReadVal' = Zero
  /\ UNCHANGED <<storePresent, storeVal, cachePresent, cacheVal>>

Invalidate(k) ==
  /\ k \in Keys
  /\ cachePresent' = [cachePresent EXCEPT ![k] = FALSE]
  /\ cacheVal' = [cacheVal EXCEPT ![k] = Zero]
  /\ UNCHANGED <<storePresent, storeVal, lastReadValid, lastReadKey, lastReadVal>>

Next ==
  \/ \E k \in Keys, v \in Vals : CacheWrite(k, v)
  \/ \E k \in Keys : CacheReadHit(k)
  \/ \E k \in Keys : CacheReadMiss(k)
  \/ \E k \in Keys : CacheReadAbsent(k)
  \/ \E k \in Keys : Invalidate(k)

Spec == Init /\ [][Next]_vars

Inv ==
  /\ \A k \in Keys : cachePresent[k] => /\ storePresent[k]
                                        /\ cacheVal[k] = storeVal[k]
  /\ lastReadValid => /\ storePresent[lastReadKey]
                      /\ lastReadVal = storeVal[lastReadKey]

Property == Inv
====
