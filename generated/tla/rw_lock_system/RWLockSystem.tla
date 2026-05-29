---- MODULE RWLockSystem ----
EXTENDS Naturals, FiniteSets

CONSTANTS Clients, MaxReaders

VARIABLES state, reader_count, client_state, pcL, pcC

vars == << state, reader_count, client_state, pcL, pcC >>

ReadersSet == { c \in Clients : client_state[c] = "reading" }
WritersSet == { c \in Clients : client_state[c] = "writing" }

TypeOK ==
  /\ state \in {"free","read","write"}
  /\ reader_count \in 0..MaxReaders
  /\ client_state \in [Clients -> {"idle","reading","writing"}]

LockInit ==
  /\ state = "free"
  /\ reader_count = 0
  /\ pcL = "Loop"

ClientsInit ==
  /\ client_state = [c \in Clients |-> "idle"]
  /\ pcC = "Loop"

Init == LockInit /\ ClientsInit

LockStep ==
  /\ pcL = "Loop"
  /\ \/ /\ state \in {"free","read"}
        /\ reader_count < MaxReaders
        /\ state' = "read"
        /\ reader_count' = reader_count + 1
     \/ /\ state = "read"
        /\ reader_count > 0
        /\ reader_count' = reader_count - 1
        /\ state' = IF reader_count - 1 = 0 THEN "free" ELSE "read"
     \/ /\ state = "free"
        /\ reader_count = 0
        /\ state' = "write"
        /\ UNCHANGED reader_count
     \/ /\ state = "write"
        /\ state' = "free"
        /\ UNCHANGED reader_count
  /\ pcL' = "Loop"
  /\ UNCHANGED <<client_state, pcC>>

ClientsStep ==
  /\ pcC = "Loop"
  /\ \E c \in Clients :
       \/ /\ client_state[c] = "idle"
          /\ \A o \in Clients : client_state[o] # "writing"
          /\ client_state' = [client_state EXCEPT ![c] = "reading"]
       \/ /\ client_state[c] = "reading"
          /\ client_state' = [client_state EXCEPT ![c] = "idle"]
       \/ /\ client_state[c] = "idle"
          /\ \A o \in Clients : client_state[o] = "idle"
          /\ client_state' = [client_state EXCEPT ![c] = "writing"]
       \/ /\ client_state[c] = "writing"
          /\ client_state' = [client_state EXCEPT ![c] = "idle"]
  /\ pcC' = "Loop"
  /\ UNCHANGED <<state, reader_count, pcL>>

Next == LockStep \/ ClientsStep

Spec == Init /\ [][Next]_vars

Inv ==
  /\ TypeOK
  /\ (state = "write") => (reader_count = 0 /\ Cardinality(WritersSet) <= 1)
  /\ (state = "free") => (reader_count = 0 /\ ReadersSet = {} /\ WritersSet = {})
  /\ (\E c \in Clients : client_state[c] = "reading") => (state = "read" /\ reader_count >= 1)
  /\ (\E c \in Clients : client_state[c] = "writing") => (state = "write")
  /\ Cardinality(WritersSet) <= 1
  /\ ~(ReadersSet # {} /\ WritersSet # {})

Property ==
  /\ (state = "write") => (reader_count = 0 /\ Cardinality(WritersSet) <= 1)
  /\ (\E c \in Clients : client_state[c] = "reading") => (state = "read" /\ reader_count >= 1)
  /\ (state = "free") => (reader_count = 0 /\ ReadersSet = {} /\ WritersSet = {})
====
