---- MODULE Clients_Abs ----
EXTENDS Naturals, FiniteSets

CONSTANTS Clients

VARIABLES client_state

vars == << client_state >>

TypeOK == client_state \in [Clients -> {"idle","reading","writing"}]

Init == client_state = [c \in Clients |-> "idle"]

StartRead(c) ==
  /\ client_state[c] = "idle"
  /\ \A o \in Clients : client_state[o] # "writing"
  /\ client_state' = [client_state EXCEPT ![c] = "reading"]

FinishRead(c) ==
  /\ client_state[c] = "reading"
  /\ client_state' = [client_state EXCEPT ![c] = "idle"]

StartWrite(c) ==
  /\ client_state[c] = "idle"
  /\ \A o \in Clients : client_state[o] = "idle"
  /\ client_state' = [client_state EXCEPT ![c] = "writing"]

FinishWrite(c) ==
  /\ client_state[c] = "writing"
  /\ client_state' = [client_state EXCEPT ![c] = "idle"]

Next == \E c \in Clients :
  StartRead(c) \/ FinishRead(c) \/ StartWrite(c) \/ FinishWrite(c)

Spec == Init /\ [][Next]_vars

WritersSet == { c \in Clients : client_state[c] = "writing" }
ReadersSet == { c \in Clients : client_state[c] = "reading" }

Inv ==
  /\ TypeOK
  /\ Cardinality(WritersSet) <= 1
  /\ ~(ReadersSet # {} /\ WritersSet # {})
====
