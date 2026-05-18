class PetPianoCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = config;
  }

  static getStubConfig() {
    return { entity_prefix: "pet_piano" };
  }

  _e(key) {
    const prefix = this._config.entity_prefix || "pet_piano";
    return this._hass.states[`${key.includes(".") ? key : prefix + "." + key}`];
  }

  _state(key, fallback = "—") {
    const e = this._e(key);
    return e ? e.state : fallback;
  }

  _num(key, fallback = 0) {
    const v = parseFloat(this._state(key, fallback));
    return isNaN(v) ? fallback : v;
  }

  _render() {
    if (!this._hass || !this._config) return;

    const battery   = this._num("sensor.pet_piano_battery", 0);
    const food      = this._num("sensor.pet_piano_food_level", 0);
    const portions  = this._num("sensor.pet_piano_portions_today", 0);
    const mode      = this._state("sensor.pet_piano_mode", "Normal");
    const volume    = this._num("number.pet_piano_volume", 3);
    const level     = this._num("number.pet_piano_tutor_level", 0);
    const motorJam  = this._state("binary_sensor.pet_piano_motor_jam") === "on";
    const wallPower = this._state("binary_sensor.pet_piano_wall_power") === "on";
    const schedOn   = this._state("switch.pet_piano_schedule") === "on";

    const m1time    = this._state("sensor.pet_piano_meal_1_time", "—");
    const m2time    = this._state("sensor.pet_piano_meal_2_time", "—");
    const m3time    = this._state("sensor.pet_piano_meal_3_time", "—");
    const m1active  = this._state("binary_sensor.pet_piano_meal_1_active") === "on";
    const m2active  = this._state("binary_sensor.pet_piano_meal_2_active") === "on";
    const m3active  = this._state("binary_sensor.pet_piano_meal_3_active") === "on";

    const battColor = battery > 30 ? "var(--success-color,#4caf50)" : battery > 15 ? "#ff9800" : "#f44336";
    const foodDots  = Array.from({length: 7}, (_, i) =>
      `<div style="width:8px;height:8px;border-radius:50%;background:${i < food ? battColor : "var(--divider-color,#e0e0e0)"}"></div>`
    ).join("");

    const modes = ["Normal", "Tutor", "Concert"];
    const modeTabs = modes.map(m => {
      const active = mode === m;
      return `<button data-mode="${m}" style="flex:1;padding:5px 0;font-size:11px;border:1px solid ${active ? "var(--primary-color)" : "var(--divider-color,#e0e0e0)"};border-radius:6px;background:${active ? "var(--primary-color)" : "transparent"};color:${active ? "#fff" : "var(--secondary-text-color)"};cursor:pointer;font-family:inherit;transition:all .15s">${m}</button>`;
    }).join("");

    const mealRow = (label, time, active) => {
      const disabled = time === "Disabled" || time === "—";
      return `
      <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--divider-color,#e0e0e0);border-radius:8px">
        <div style="width:8px;height:8px;border-radius:50%;flex-shrink:0;background:${active ? battColor : "var(--divider-color,#e0e0e0)"}"></div>
        <div style="font-size:12px;color:var(--secondary-text-color);width:44px;flex-shrink:0">${label}</div>
        <div style="font-size:13px;font-weight:500;flex:1;color:${disabled ? "var(--secondary-text-color)" : "var(--primary-text-color)"}">${time}</div>
      </div>`;
    };

    this.innerHTML = `
<ha-card>
  <div style="padding:16px;font-family:var(--paper-font-body1_-_font-family,Roboto)">

    <!-- Header -->
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:38px;height:38px;border-radius:10px;background:var(--primary-color);display:flex;align-items:center;justify-content:center">
          <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
            <rect x="2" y="5" width="16" height="10" rx="1.5" fill="white" opacity=".2"/>
            <rect x="3.5" y="5" width="2" height="7" rx=".4" fill="white" opacity=".9"/>
            <rect x="6.5" y="5" width="2" height="7" rx=".4" fill="white" opacity=".9"/>
            <rect x="9.5" y="5" width="2" height="7" rx=".4" fill="white" opacity=".9"/>
            <rect x="12.5" y="5" width="2" height="7" rx=".4" fill="white" opacity=".9"/>
            <rect x="15.5" y="5" width="1.5" height="7" rx=".4" fill="white" opacity=".9"/>
            <rect x="5" y="5" width="1.5" height="4.5" rx=".3" fill="white"/>
            <rect x="8" y="5" width="1.5" height="4.5" rx=".3" fill="white"/>
            <rect x="13.5" y="5" width="1.5" height="4.5" rx=".3" fill="white"/>
          </svg>
        </div>
        <div>
          <div style="font-size:15px;font-weight:500;color:var(--primary-text-color)">Pet Piano</div>
          <div style="font-size:11px;color:var(--secondary-text-color)">${wallPower ? "Wall power" : "Battery"} · Vol ${volume}/7</div>
        </div>
      </div>
      ${motorJam
        ? `<div style="font-size:11px;padding:3px 10px;border-radius:20px;background:#fff3e0;color:#e65100;font-weight:500">Motor jam!</div>`
        : `<div style="font-size:11px;padding:3px 10px;border-radius:20px;background:#e8f5e9;color:#2e7d32;font-weight:500">Online</div>`
      }
    </div>

    <!-- Mode tabs -->
    <div style="display:flex;gap:4px;margin-bottom:14px">${modeTabs}</div>

    <!-- Metrics -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px">
      <div style="background:var(--secondary-background-color,#f5f5f5);border-radius:8px;padding:10px 12px">
        <div style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px">Battery</div>
        <div style="font-size:20px;font-weight:500;color:var(--primary-text-color);line-height:1">${battery}<span style="font-size:12px">%</span></div>
        <div style="height:3px;background:var(--divider-color,#e0e0e0);border-radius:2px;margin-top:6px">
          <div style="height:3px;border-radius:2px;background:${battColor};width:${battery}%"></div>
        </div>
      </div>
      <div style="background:var(--secondary-background-color,#f5f5f5);border-radius:8px;padding:10px 12px">
        <div style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px">Food level</div>
        <div style="font-size:20px;font-weight:500;color:var(--primary-text-color);line-height:1">${food}<span style="font-size:12px">/7</span></div>
        <div style="display:flex;gap:3px;margin-top:6px">${foodDots}</div>
      </div>
      <div style="background:var(--secondary-background-color,#f5f5f5);border-radius:8px;padding:10px 12px">
        <div style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px">Today</div>
        <div style="font-size:20px;font-weight:500;color:var(--primary-text-color);line-height:1">${portions}</div>
        <div style="font-size:11px;color:var(--secondary-text-color);margin-top:2px">portions</div>
      </div>
    </div>

    <!-- Tutor level (only in tutor mode) -->
    ${mode === "Tutor" ? `
    <div style="margin-bottom:14px;padding:10px 12px;background:var(--secondary-background-color,#f5f5f5);border-radius:8px">
      <div style="display:flex;justify-content:space-between;margin-bottom:6px">
        <div style="font-size:12px;color:var(--secondary-text-color)">Tutor level (keys to press)</div>
        <div style="font-size:12px;font-weight:500;color:var(--primary-text-color)">${level}/7</div>
      </div>
      <input type="range" min="0" max="7" value="${level}" id="pp-level-slider"
        style="width:100%;accent-color:var(--primary-color)">
    </div>` : ""}

    <!-- Schedule -->
    <div style="font-size:11px;color:var(--secondary-text-color);margin-bottom:8px;display:flex;align-items:center;justify-content:space-between">
      <span style="text-transform:uppercase;letter-spacing:.05em">Schedule</span>
      <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
        <span style="font-size:11px">${schedOn ? "On" : "Off"}</span>
        <div id="pp-sched-toggle" style="width:28px;height:16px;border-radius:8px;background:${schedOn ? "var(--primary-color)" : "var(--divider-color,#ccc)"};position:relative;cursor:pointer;transition:background .2s">
          <div style="position:absolute;top:2px;left:${schedOn ? "14px" : "2px"};width:12px;height:12px;border-radius:50%;background:#fff;transition:left .2s"></div>
        </div>
      </label>
    </div>
    <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px">
      ${mealRow("Meal 1", m1time, m1active)}
      ${mealRow("Meal 2", m2time, m2active)}
      ${mealRow("Meal 3", m3time, m3active)}
    </div>

    <!-- Actions -->
    <div style="display:flex;gap:8px">
      <button id="pp-dispense" style="flex:2;padding:9px;border:none;border-radius:8px;background:var(--primary-color);color:#fff;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:opacity .15s">
        Dispense now
      </button>
      <button id="pp-sync" style="flex:1;padding:9px;border:1px solid var(--divider-color,#e0e0e0);border-radius:8px;background:transparent;color:var(--primary-text-color);font-size:13px;cursor:pointer;font-family:inherit">
        Sync time
      </button>
    </div>

  </div>
</ha-card>`;

    this._attachHandlers(schedOn);
  }

  _attachHandlers(schedOn) {
    const btn = this.querySelector("#pp-dispense");
    if (btn) btn.onclick = () => {
      btn.textContent = "Dispensing…";
      btn.disabled = true;
      this._hass.callService("button", "press", {
        entity_id: "button.pet_piano_dispense_now"
      }).finally(() => {
        setTimeout(() => { btn.textContent = "Dispense now"; btn.disabled = false; }, 2000);
      });
    };

    const sync = this.querySelector("#pp-sync");
    if (sync) sync.onclick = () => {
      sync.textContent = "Syncing…";
      this._hass.callService("button", "press", {
        entity_id: "button.pet_piano_sync_rtc"
      }).finally(() => {
        setTimeout(() => { sync.textContent = "Sync time"; }, 1500);
      });
    };

    const toggle = this.querySelector("#pp-sched-toggle");
    if (toggle) toggle.onclick = () => {
      this._hass.callService("switch", schedOn ? "turn_off" : "turn_on", {
        entity_id: "switch.pet_piano_schedule"
      });
    };

    const slider = this.querySelector("#pp-level-slider");
    if (slider) slider.onchange = (e) => {
      this._hass.callService("number", "set_value", {
        entity_id: "number.pet_piano_tutor_level",
        value: parseInt(e.target.value)
      });
    };

    this.querySelectorAll("[data-mode]").forEach(btn => {
      btn.onclick = () => {
        const modeMap = {"Normal": 0, "Tutor": 1, "Concert": 2};
        this._hass.callService("select", "select_option", {
          entity_id: "select.pet_piano_mode",
          option: btn.dataset.mode
        }).catch(() => {});
      };
    });
  }

  getCardSize() { return 5; }
}

customElements.define("pet-piano-card", PetPianoCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "pet-piano-card",
  name: "Pet Piano",
  description: "Control card for Pet Piano BLE device",
  preview: true,
});
