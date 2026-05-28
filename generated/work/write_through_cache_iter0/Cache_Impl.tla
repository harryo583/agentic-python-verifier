---- MODULE Cache_Impl ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Keys, Vals, Missing

(* --algorithm Cache
variables
  store = [k \in Keys |-> Missing],
  cache = [k \in Keys |-> Missing],
  lastRead = Missing;
begin
  Loop:
    while TRUE do
      either
        \* Write: update both cache and store atomically
        with k \in Keys, v \in Vals do
          cache[k] := v ||
          store[k] := v;
          lastRead := Missing;
        end with;
      or
        \* Read hit
        with k \in Keys do
          if cache[k] # Missing then
            lastRead := [key |-> k, val |-> cache[k]];
          else
            \* Read miss: populate cache from store
            cache[k] := store[k];
            lastRead := [key |-> k, val |-> store[k]];
          end if;
        end with;
      or
        \* Invalidate a cache entry
        with k \in Keys do
          cache[k] := Missing;
        end with;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "63c73fca" /\ chksum(tla) = "93e18af5")
VARIABLES store, cache, lastRead

vars == << store, cache, lastRead >>

Init == (* Global variables *)
        /\ store = [k \in Keys |-> Missing]
        /\ cache = [k \in Keys |-> Missing]
        /\ lastRead = Missing

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  /\ /\ cache' = [cache EXCEPT ![k] = v]
                     /\ store' = [store EXCEPT ![k] = v]
                  /\ lastRead' = Missing
        \/ /\ \E k \in Keys:
                IF cache[k] # Missing
                   THEN /\ lastRead' = [key |-> k, val |-> cache[k]]
                        /\ cache' = cache
                   ELSE /\ cache' = [cache EXCEPT ![k] = store[k]]
                        /\ lastRead' = [key |-> k, val |-> store[k]]
           /\ store' = store
        \/ /\ \E k \in Keys:
                cache' = [cache EXCEPT ![k] = Missing]
           /\ UNCHANGED <<store, lastRead>>

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

InvImpl ==
  /\ DOMAIN store = Keys
  /\ DOMAIN cache = Keys
  /\ \A k \in Keys : store[k] \in (Vals \cup {Missing})
  /\ \A k \in Keys : cache[k] \in (Vals \cup {Missing})
  /\ \A k \in Keys : (cache[k] # Missing) => (cache[k] = store[k])
  /\ \/ lastRead = Missing
     \/ /\ lastRead.key \in Keys
        /\ lastRead.val \in (Vals \cup {Missing})
        /\ lastRead.val = store[lastRead.key]

PropertyImpl == InvImpl
====
