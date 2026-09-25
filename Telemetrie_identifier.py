"""Identifier fuer das HV Accumulator Management System."""

Device_AMS = 0xA1

ID_TS_Voltage                       = 0x21
ID_TS_Current                       = 0x22
ID_TS_Currentdrawn                  = 0x23
ID_TS_AMS_Status                    = 0x24
ID_TS_Cell_Voltages_max             = 0x25
ID_TS_Cell_Voltages_min             = 0x26
ID_TS_Cell_Temprearure_max          = 0x27
ID_TS_Cell_Temprearure_min          = 0x28
ID_TS_Cellnumer_Voltages_max        = 0x29
ID_TS_Cellnumer_Voltages_min        = 0x2A
ID_TS_Cellnumer_Temprearure_max     = 0x2B
ID_TS_Cellnumer_Temprearure_min     = 0x2C
ID_LTC_Temperature                  = 0x2D
ID_TS_All_Cell_Voltages             = 0x2E
ID_TS_All_Cell_Temperatures         = 0x2F
ID_TS_Stack_Detail                  = 0x40
ID_LTC_All_Stacks = 0x90

ID_MAP = {
    33:  {"name": "ID_TS_Voltage",                        "group": "TSAC"},
    34:  {"name": "ID_TS_Current",                        "group": "TSAC"},
    35:  {"name": "ID_TS_Currentdrawn",                   "group": "TSAC"},
    36:  {"name": "ID_TS_AMS_Status",                     "group": "TSAC"},
    37:  {"name": "ID_TS_Cell_Voltages_max",              "group": "TSAC"},
    38:  {"name": "ID_TS_Cell_Voltages_min",              "group": "TSAC"},
    39:  {"name": "ID_TS_Cell_Temprearure_max",           "group": "TSAC"},
    40:  {"name": "ID_TS_Cell_Temprearure_min",           "group": "TSAC"},
    41:  {"name": "ID_TS_Cellnumer_Voltages_max",         "group": "TSAC"},
    42:  {"name": "ID_TS_Cellnumer_Voltages_min",         "group": "TSAC"},
    43:  {"name": "ID_TS_Cellnumer_Temprearure_max",      "group": "TSAC"},
    44:  {"name": "ID_TS_Cellnumer_Temprearure_min",      "group": "TSAC"},
    45:  {"name": "ID_LTC_Temperatur",               "group": "LTC"},
    46: {"name": "ID_TS_All_Cell_Voltages",          "group": "TSAC"},
    47: {"name": "ID_TS_All_Cell_Temperatures",      "group": "TSAC"},
    64: {"name": "ID_TS_Stack_Detail",               "group": "TSAC"},
    ID_LTC_All_Stacks: {"name": "ID_LTC_All_Stacks", "group": "LTC"},
}


def build_frontend_id_map():
    frontend_map = {}

    for raw_id, info in ID_MAP.items():
        frontend_map[str(raw_id)] = {
            "label": info["name"],
            "group": info["group"],
            "icon": info["name"],
        }
        frontend_map[info["name"]] = {
            "label": info["name"],
            "group": info["group"],
            "icon": info["name"],
        }

    frontend_map.update({
        "Stacks": {"label": "Stacks", "group": "Stacks", "icon": "default"},
        "stack_index": {"label": "Stack Index", "group": "Stacks", "icon": "default"},
        "stack_number": {"label": "Stack Nummer", "group": "Stacks", "icon": "default"},
        "sum_voltage_v": {"label": "Gesamtspannung", "group": "Stacks", "icon": "default"},
        "avg_temp_c": {"label": "Durchschnitt Temperatur", "group": "Stacks", "icon": "default"},
        "max_temp_c": {"label": "Max Temperatur", "group": "Stacks", "icon": "default"},
        "min_temp_c": {"label": "Min Temperatur", "group": "Stacks", "icon": "default"},
        "ltc_temp_c": {"label": "LTC Temperatur", "group": "Stacks", "icon": "default"},
        "ltc_ts": {"label": "LTC Zeitstempel", "group": "Stacks", "icon": "default"},
        "cell_voltages_v": {"label": "Zellspannungen", "group": "Stacks", "icon": "default"},
        "cell_temperatures_c": {"label": "Zelltemperaturen", "group": "Stacks", "icon": "default"},
        "cells": {"label": "Zellen", "group": "Stacks", "icon": "default"},
        "ts": {"label": "Zeitstempel", "group": "System", "icon": "default"},
    })

    for stack_number in range(1, 13):
        frontend_map[f"Stack_{stack_number:02d}"] = {
            "label": f"Stack {stack_number}",
            "group": "Stacks",
            "icon": "default",
        }

    for cell_number in range(1, 13):
        frontend_map[f"cell_{cell_number:02d}_voltage_v"] = {
            "label": f"Cell {cell_number} Voltage",
            "group": "Stacks",
            "icon": "default",
        }
        frontend_map[f"cell_{cell_number:02d}_temperature_c"] = {
            "label": f"Cell {cell_number} Temperature",
            "group": "Stacks",
            "icon": "default",
        }

    return frontend_map


FRONTEND_ID_MAP = build_frontend_id_map()
