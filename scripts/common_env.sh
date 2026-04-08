#!/usr/bin/env bash
# common_env.sh — Shared ROS/workspace environment bootstrap for AGV_sim.
#
# Priority order:
#   1. Reuse the ROS distro already loaded in the caller shell (ROS_DISTRO)
#   2. Use AGV_ROS_DISTRO if explicitly provided by the user
#   3. Auto-detect an installed distro from a known list
#
# This file is meant to be sourced:
#   source "$(dirname "$0")/common_env.sh"

_agv_common_env_fail() {
  echo "[common_env] Error: $*" >&2
  return 1 2>/dev/null || exit 1
}

_agv_common_env_note() {
  echo "[common_env] $*"
}

AGV_COMMON_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGV_PROJECT_ROOT="$(cd "${AGV_COMMON_ENV_DIR}/.." && pwd)"
export AGV_COMMON_ENV_DIR
export AGV_PROJECT_ROOT

_agv_ros_candidates=()
if [[ -n "${ROS_DISTRO:-}" ]]; then
  _agv_ros_candidates+=("${ROS_DISTRO}")
fi
if [[ -n "${AGV_ROS_DISTRO:-}" ]]; then
  _already_listed=0
  for _candidate in "${_agv_ros_candidates[@]}"; do
    if [[ "${_candidate}" == "${AGV_ROS_DISTRO}" ]]; then
      _already_listed=1
      break
    fi
  done
  if [[ "${_already_listed}" -eq 0 ]]; then
    _agv_ros_candidates+=("${AGV_ROS_DISTRO}")
  fi
fi
for _candidate in jazzy humble iron rolling; do
  _already_listed=0
  for _listed in "${_agv_ros_candidates[@]}"; do
    if [[ "${_listed}" == "${_candidate}" ]]; then
      _already_listed=1
      break
    fi
  done
  if [[ "${_already_listed}" -eq 0 ]]; then
    _agv_ros_candidates+=("${_candidate}")
  fi
done

AGV_ROS_SETUP=""
AGV_ROS_DISTRO_SELECTED=""
for _candidate in "${_agv_ros_candidates[@]}"; do
  if [[ -f "/opt/ros/${_candidate}/setup.bash" ]]; then
    AGV_ROS_SETUP="/opt/ros/${_candidate}/setup.bash"
    AGV_ROS_DISTRO_SELECTED="${_candidate}"
    break
  fi
done

if [[ -z "${AGV_ROS_SETUP}" ]]; then
  _agv_common_env_fail "No supported ROS 2 setup file found. Tried: ${_agv_ros_candidates[*]}"
fi

set +u
source "${AGV_ROS_SETUP}"
set -u

export AGV_ROS_DISTRO_SELECTED

AGV_WS_SETUP="${AGV_PROJECT_ROOT}/install/setup.bash"
AGV_WS_SETUP_LOADED=0
if [[ -f "${AGV_WS_SETUP}" ]]; then
  set +u
  source "${AGV_WS_SETUP}"
  set -u
  AGV_WS_SETUP_LOADED=1
else
  _agv_common_env_note "Workspace overlay not found at ${AGV_WS_SETUP}"
  _agv_common_env_note "Run 'colcon build --symlink-install' on this machine before launching the full stack."
fi
export AGV_WS_SETUP
export AGV_WS_SETUP_LOADED

_agv_common_env_note "PROJECT_ROOT=${AGV_PROJECT_ROOT}"
_agv_common_env_note "ROS_DISTRO=${ROS_DISTRO:-${AGV_ROS_DISTRO_SELECTED}}"
if [[ "${AGV_WS_SETUP_LOADED}" -eq 1 ]]; then
  _agv_common_env_note "Workspace overlay loaded: ${AGV_WS_SETUP}"
else
  _agv_common_env_note "Workspace overlay not loaded"
fi

AGV_COMMON_ENV_LOADED=1
export AGV_COMMON_ENV_LOADED
