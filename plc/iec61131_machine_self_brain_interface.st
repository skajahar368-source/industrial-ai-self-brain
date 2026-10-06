(*
 Machine Self-Brain - Vendor-Neutral IEC 61131-3 PLC Interface
 ----------------------------------------------------------------
 Purpose:
   Provide a real PLC-side interface matching the Self-Brain ML telemetry
   contract. The PLC remains responsible for sequence, interlocks, alarms,
   and physical outputs. Self-Brain receives read-only telemetry.

 IMPORTANT:
   - Map these tags to actual I/O only after machine-specific validation.
   - Keep E-Stop and safety functions in certified safety hardware/programs.
   - This program contains NO ML commands and NO remote machine-control write
     from Self-Brain.
*)

TYPE E_MACHINE_STATE :
(
    STATE_OFFLINE,
    STATE_STARTING,
    STATE_RUNNING,
    STATE_WARNING,
    STATE_DEGRADED,
    STATE_FAULT,
    STATE_STOPPING,
    STATE_MAINTENANCE
);
END_TYPE

TYPE E_FAULT_CODE :
(
    FAULT_NONE,
    FAULT_HIGH_TEMP,
    FAULT_HIGH_PRESSURE,
    FAULT_HIGH_VIBRATION,
    FAULT_HIGH_TEMP_PRESSURE,
    FAULT_MULTI_PARAMETER
);
END_TYPE

VAR_GLOBAL
    (* ===== Physical / machine inputs ===== *)
    DI_EStopOK           : BOOL;
    DI_SafetyOK           : BOOL;
    DI_StartRequest       : BOOL;
    DI_StopRequest        : BOOL;
    DI_ResetRequest       : BOOL;
    DI_MaintenanceMode    : BOOL;
    DI_CycleComplete      : BOOL;

    AI_TemperatureC       : REAL;
    AI_PressureBar        : REAL;
    AI_VibrationMmS       : REAL;

    (* ===== Machine outputs ===== *)
    DO_MachineEnable      : BOOL;
    DO_RunCommand         : BOOL;
    DO_FaultLamp          : BOOL;

    (* ===== Self-Brain read-only telemetry contract ===== *)
    SB_MachineID          : STRING[32] := 'M-001';
    SB_State              : E_MACHINE_STATE := STATE_OFFLINE;
    SB_Mode               : STRING[16] := 'AUTO';
    SB_CycleCount         : DINT := 0;
    SB_DowntimeMinutes    : REAL := 0.0;
    SB_RuntimeMinutes     : REAL := 0.0;
    SB_TemperatureC       : REAL := 0.0;
    SB_PressureBar        : REAL := 0.0;
    SB_VibrationMmS       : REAL := 0.0;
    SB_FaultCode          : E_FAULT_CODE := FAULT_NONE;
    SB_AlarmActive        : BOOL := FALSE;
    SB_Heartbeat          : UDINT := 0;

    (* ===== Limits; replace with validated machine limits ===== *)
    CFG_TempWarningC      : REAL := 65.0;
    CFG_TempFaultC        : REAL := 80.0;
    CFG_PressureHighBar   : REAL := 100.0;
    CFG_PressureLowBar    : REAL := 30.0;
    CFG_VibrationWarning  : REAL := 5.0;
    CFG_VibrationFault    : REAL := 8.0;
END_VAR


VAR
    tScan                 : TON;
    tRuntime              : TON;
    StateBefore           : E_MACHINE_STATE;
    CycleEdge             : BOOL;
    PreviousCycle         : BOOL;
    TempHigh              : BOOL;
    PressureHigh          : BOOL;
    PressureLow           : BOOL;
    VibrationHigh         : BOOL;
    CriticalFault         : BOOL;
END_VAR


(* ================================================================
   1. Read and normalize machine telemetry
   ================================================================ *)
SB_TemperatureC := AI_TemperatureC;
SB_PressureBar := AI_PressureBar;
SB_VibrationMmS := AI_VibrationMmS;

TempHigh := SB_TemperatureC >= CFG_TempFaultC;
PressureHigh := SB_PressureBar >= CFG_PressureHighBar;
PressureLow := (SB_PressureBar > 0.0) AND
               (SB_PressureBar < CFG_PressureLowBar);
VibrationHigh := SB_VibrationMmS >= CFG_VibrationFault;


(* ================================================================
   2. Determine PLC fault code
   ================================================================ *)
SB_FaultCode := FAULT_NONE;

IF TempHigh AND (PressureHigh OR PressureLow) THEN
    SB_FaultCode := FAULT_HIGH_TEMP_PRESSURE;
ELSIF TempHigh THEN
    SB_FaultCode := FAULT_HIGH_TEMP;
ELSIF PressureHigh OR PressureLow THEN
    SB_FaultCode := FAULT_HIGH_PRESSURE;
ELSIF VibrationHigh THEN
    SB_FaultCode := FAULT_HIGH_VIBRATION;
END_IF;

CriticalFault :=
    (SB_FaultCode = FAULT_HIGH_TEMP_PRESSURE) OR
    (SB_FaultCode = FAULT_MULTI_PARAMETER);

SB_AlarmActive := SB_FaultCode <> FAULT_NONE;


(* ================================================================
   3. Safety/interlock layer
   Safety must be implemented/validated according to the machine's
   actual risk assessment and applicable safety standard.
   ================================================================ *)
IF NOT DI_EStopOK OR NOT DI_SafetyOK THEN
    DO_MachineEnable := FALSE;
    DO_RunCommand := FALSE;
    SB_State := STATE_FAULT;
ELSIF CriticalFault OR TempHigh OR PressureHigh OR
      PressureLow OR VibrationHigh THEN
    DO_MachineEnable := FALSE;
    DO_RunCommand := FALSE;
    SB_State := STATE_FAULT;
ELSIF DI_MaintenanceMode THEN
    DO_MachineEnable := FALSE;
    DO_RunCommand := FALSE;
    SB_State := STATE_MAINTENANCE;
ELSIF DI_StopRequest THEN
    DO_RunCommand := FALSE;
    SB_State := STATE_STOPPING;
ELSIF DI_StartRequest THEN
    DO_MachineEnable := TRUE;
    SB_State := STATE_STARTING;

    (* Actual machine-specific startup sequence belongs here. *)
    IF DI_SafetyOK AND DI_EStopOK THEN
        DO_RunCommand := TRUE;
        SB_State := STATE_RUNNING;
    END_IF;
ELSE
    DO_MachineEnable := TRUE;
    DO_RunCommand := TRUE;

    IF (SB_TemperatureC >= CFG_TempWarningC) OR
       (SB_VibrationMmS >= CFG_VibrationWarning) THEN
        SB_State := STATE_WARNING;
    ELSE
        SB_State := STATE_RUNNING;
    END_IF;
END_IF;


(* ================================================================
   4. Production cycle counter
   ================================================================ *)
CycleEdge := DI_CycleComplete AND NOT PreviousCycle;
PreviousCycle := DI_CycleComplete;

IF CycleEdge AND
   ((SB_State = STATE_RUNNING) OR (SB_State = STATE_WARNING)) THEN
    SB_CycleCount := SB_CycleCount + 1;
END_IF;


(* ================================================================
   5. Runtime / downtime accounting
   Replace the 1-second timing implementation with the PLC's actual
   cycle-time clock/timer mechanism during commissioning.
   ================================================================ *)
IF DO_RunCommand AND (SB_State <> STATE_FAULT) AND
   (SB_State <> STATE_MAINTENANCE) THEN
    SB_RuntimeMinutes := SB_RuntimeMinutes + 0.0166667;
ELSE
    SB_DowntimeMinutes := SB_DowntimeMinutes + 0.0166667;
END_IF;


(* ================================================================
   6. Heartbeat for gateway/SCADA
   ================================================================ *)
SB_Heartbeat := SB_Heartbeat + 1;

DO_FaultLamp := SB_AlarmActive;


(* ================================================================
   7. Self-Brain boundary
   There is intentionally NO assignment such as:
       DO_RunCommand := SelfBrainCommand
   Self-Brain can consume SB_* values through OPC UA/Modbus/MQTT
   via a gateway, but does not directly control the machine here.
   ================================================================ *)
