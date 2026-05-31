class PetPianoCard extends HTMLElement {
  constructor() {
    super();
    this._initialized = false;
    this._volDragging = false;
    this._levelDragging = false;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) {
      this._buildDOM();
      this._attachHandlers();
      this._initialized = true;
    }
    this._update();
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

  _buildDOM() {
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
          <div class="pp-subtitle" style="font-size:11px;color:var(--secondary-text-color)"></div>
        </div>
      </div>
      <div class="pp-status" style="font-size:11px;padding:3px 10px;border-radius:20px;font-weight:500"></div>
    </div>

    <!-- Mode tabs -->
    <div style="display:flex;gap:4px;margin-bottom:14px">
      <button data-mode="Normal" style="flex:1;padding:5px 0;font-size:11px;border-radius:6px;cursor:pointer;font-family:inherit;transition:all .15s">Normal</button>
      <button data-mode="Tutor"  style="flex:1;padding:5px 0;font-size:11px;border-radius:6px;cursor:pointer;font-family:inherit;transition:all .15s">Tutor</button>
      <button data-mode="Concert" style="flex:1;padding:5px 0;font-size:11px;border-radius:6px;cursor:pointer;font-family:inherit;transition:all .15s">Concert</button>
    </div>

    <!-- Metrics -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px">
      <div style="background:var(--secondary-background-color,#f5f5f5);border-radius:8px;padding:10px 12px">
        <div style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px">Battery</div>
        <div class="pp-bat-val" style="font-size:20px;font-weight:500;color:var(--primary-text-color);line-height:1"></div>
        <div style="height:3px;background:var(--divider-color,#e0e0e0);border-radius:2px;margin-top:6px">
          <div class="pp-bat-bar" style="height:3px;border-radius:2px;width:0%"></div>
        </div>
      </div>
      <div style="background:var(--secondary-background-color,#f5f5f5);border-radius:8px;padding:10px 12px">
        <div style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px">Food level</div>
        <div class="pp-food-val" style="font-size:20px;font-weight:500;color:var(--primary-text-color);line-height:1"></div>
        <div class="pp-food-dots" style="display:flex;gap:3px;margin-top:6px"></div>
      </div>
      <div style="background:var(--secondary-background-color,#f5f5f5);border-radius:8px;padding:10px 12px">
        <div style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px">Today</div>
        <div class="pp-portions-val" style="font-size:20px;font-weight:500;color:var(--primary-text-color);line-height:1"></div>
        <div style="font-size:11px;color:var(--secondary-text-color);margin-top:2px">portions</div>
      </div>
    </div>

    <!-- Volume slider -->
    <div style="margin-bottom:14px;padding:10px 14px;background:var(--secondary-background-color,#f5f5f5);border-radius:8px">
      <div style="display:flex;align-items:center;gap:10px">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--secondary-text-color)" stroke-width="2" stroke-linecap="round">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
        </svg>
        <input class="pp-vol-slider" type="range" min="0" max="7"
          style="flex:1;accent-color:var(--primary-color);height:4px">
        <div class="pp-vol-label" style="font-size:13px;font-weight:500;color:var(--primary-text-color);min-width:18px;text-align:right"></div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--secondary-text-color)" stroke-width="2" stroke-linecap="round">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
        </svg>
      </div>
      <div class="pp-vol-bars" style="display:flex;justify-content:space-between;margin-top:4px;padding:0 2px"></div>
    </div>

    <!-- Tutor level -->
    <div class="pp-tutor-wrap" style="display:none;margin-bottom:14px;padding:10px 12px;background:var(--secondary-background-color,#f5f5f5);border-radius:8px">
      <div style="display:flex;justify-content:space-between;margin-bottom:6px">
        <div style="font-size:12px;color:var(--secondary-text-color)">Tutor level (keys to press)</div>
        <div class="pp-level-label" style="font-size:12px;font-weight:500;color:var(--primary-text-color)"></div>
      </div>
      <input class="pp-level-slider" type="range" min="0" max="7"
        style="width:100%;accent-color:var(--primary-color)">
    </div>

    <!-- Schedule -->
    <div style="font-size:11px;color:var(--secondary-text-color);margin-bottom:8px;display:flex;align-items:center;justify-content:space-between">
      <span style="text-transform:uppercase;letter-spacing:.05em">Schedule</span>
      <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
        <span class="pp-sched-label" style="font-size:11px"></span>
        <div class="pp-sched-toggle" style="width:28px;height:16px;border-radius:8px;position:relative;cursor:pointer;transition:background .2s">
          <div class="pp-sched-knob" style="position:absolute;top:2px;width:12px;height:12px;border-radius:50%;background:#fff;transition:left .2s"></div>
        </div>
      </label>
    </div>
    <div class="pp-meals" style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px"></div>

    <!-- Actions -->
    <div style="display:flex;gap:8px">
      <button class="pp-dispense" style="flex:2;padding:9px;border:none;border-radius:8px;background:var(--primary-color);color:#fff;font-size:13px;font-weight:500;cursor:pointer;font-family:inherit;transition:opacity .15s">
        Dispense now
      </button>
      <button class="pp-sync" style="flex:1;padding:9px;border:1px solid var(--divider-color,#e0e0e0);border-radius:8px;background:transparent;color:var(--primary-text-color);font-size:13px;cursor:pointer;font-family:inherit">
        Sync time
      </button>
    </div>

  </div>
</ha-card>`;

    // Build vol bars once
    const barsEl = this.querySelector(".pp-vol-bars");
    this._volBars = [];
    for (let i = 0; i < 8; i++) {
      const b = document.createElement("div");
      b.style.cssText = `width:3px;height:${4+i*3}px;border-radius:2px;align-self:flex-end`;
      barsEl.appendChild(b);
      this._volBars.push(b);
    }

    // Build food dots once
    const dotsEl = this.querySelector(".pp-food-dots");
    this._foodDots = [];
    for (let i = 0; i < 7; i++) {
      const d = document.createElement("div");
      d.style.cssText = "width:8px;height:8px;border-radius:50%";
      dotsEl.appendChild(d);
      this._foodDots.push(d);
    }
  }

  _attachHandlers() {
    // Dispense
    const dispense = this.querySelector(".pp-dispense");
    dispense.onclick = () => {
      dispense.textContent = "Dispensing…";
      dispense.disabled = true;
      this._hass.callService("button", "press", { entity_id: "button.pet_piano_dispense_now" })
        .finally(() => setTimeout(() => { dispense.textContent = "Dispense now"; dispense.disabled = false; }, 2000));
    };

    // Sync
    const sync = this.querySelector(".pp-sync");
    sync.onclick = () => {
      sync.textContent = "Syncing…";
      this._hass.callService("button", "press", { entity_id: "button.pet_piano_sync_rtc" })
        .finally(() => setTimeout(() => { sync.textContent = "Sync time"; }, 1500));
    };

    // Schedule toggle
    this.querySelector(".pp-sched-toggle").onclick = () => {
      const schedOn = this._state("switch.pet_piano_schedule") === "on";
      this._hass.callService("switch", schedOn ? "turn_off" : "turn_on", { entity_id: "switch.pet_piano_schedule" });
    };

    // Volume slider — track dragging so update() doesn't fight user
    const volSlider = this.querySelector(".pp-vol-slider");
    volSlider.addEventListener("mousedown",  () => this._volDragging = true);
    volSlider.addEventListener("touchstart", () => this._volDragging = true);
    volSlider.oninput = (e) => {
      const val = parseInt(e.target.value);
      this._updateVolUI(val);
    };
    volSlider.onchange = (e) => {
      this._volDragging = false;
      this._hass.callService("number", "set_value", { entity_id: "number.pet_piano_volume", value: parseInt(e.target.value) });
    };

    // Level slider
    const levelSlider = this.querySelector(".pp-level-slider");
    levelSlider.addEventListener("mousedown",  () => this._levelDragging = true);
    levelSlider.addEventListener("touchstart", () => this._levelDragging = true);
    levelSlider.onchange = (e) => {
      this._levelDragging = false;
      this._hass.callService("number", "set_value", { entity_id: "number.pet_piano_tutor_level", value: parseInt(e.target.value) });
    };

    // Mode buttons
    this.querySelectorAll("[data-mode]").forEach(btn => {
      btn.onclick = () => {
        this._hass.callService("select", "select_option", {
          entity_id: "select.pet_piano_mode",
          option: btn.dataset.mode
        }).catch(() => {});
      };
    });
  }

  _updateVolUI(val) {
    this.querySelector(".pp-vol-label").textContent = val;
    this._volBars.forEach((b, i) => {
      b.style.background = i <= val ? "var(--primary-color)" : "var(--divider-color,#e0e0e0)";
    });
  }

  _update() {
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

    const m1time   = this._state("sensor.pet_piano_meal_1_time", "—");
    const m2time   = this._state("sensor.pet_piano_meal_2_time", "—");
    const m3time   = this._state("sensor.pet_piano_meal_3_time", "—");
    const m1active = this._state("binary_sensor.pet_piano_meal_1_active") === "on";
    const m2active = this._state("binary_sensor.pet_piano_meal_2_active") === "on";
    const m3active = this._state("binary_sensor.pet_piano_meal_3_active") === "on";

    const battColor = battery > 30 ? "var(--success-color,#4caf50)" : battery > 15 ? "#ff9800" : "#f44336";

    // Subtitle & status
    this.querySelector(".pp-subtitle").textContent = `${wallPower ? "Wall power" : "Battery"} · Vol ${volume}/7`;
    const status = this.querySelector(".pp-status");
    if (motorJam) {
      status.textContent = "Motor jam!";
      status.style.cssText = "font-size:11px;padding:3px 10px;border-radius:20px;background:#fff3e0;color:#e65100;font-weight:500";
    } else {
      status.textContent = "Online";
      status.style.cssText = "font-size:11px;padding:3px 10px;border-radius:20px;background:#e8f5e9;color:#2e7d32;font-weight:500";
    }

    // Mode tabs
    this.querySelectorAll("[data-mode]").forEach(btn => {
      const active = mode === btn.dataset.mode;
      btn.style.cssText = `flex:1;padding:5px 0;font-size:11px;border:1px solid ${active ? "var(--primary-color)" : "var(--divider-color,#e0e0e0)"};border-radius:6px;background:${active ? "var(--primary-color)" : "transparent"};color:${active ? "#fff" : "var(--secondary-text-color)"};cursor:pointer;font-family:inherit;transition:all .15s`;
    });

    // Battery
    this.querySelector(".pp-bat-val").innerHTML = `${battery}<span style="font-size:12px">%</span>`;
    const batBar = this.querySelector(".pp-bat-bar");
    batBar.style.background = battColor;
    batBar.style.width = battery + "%";

    // Food
    this.querySelector(".pp-food-val").innerHTML = `${food}<span style="font-size:12px">/7</span>`;
    this._foodDots.forEach((d, i) => { d.style.background = i < food ? battColor : "var(--divider-color,#e0e0e0)"; });

    // Portions
    this.querySelector(".pp-portions-val").textContent = portions;

    // Volume — don't override if user is dragging
    if (!this._volDragging) {
      this.querySelector(".pp-vol-slider").value = volume;
      this._updateVolUI(volume);
    }

    // Tutor level
    const tutorWrap = this.querySelector(".pp-tutor-wrap");
    tutorWrap.style.display = mode === "Tutor" ? "" : "none";
    if (mode === "Tutor" && !this._levelDragging) {
      this.querySelector(".pp-level-slider").value = level;
      this.querySelector(".pp-level-label").textContent = level + "/7";
    }

    // Schedule toggle
    this.querySelector(".pp-sched-label").textContent = schedOn ? "On" : "Off";
    const toggle = this.querySelector(".pp-sched-toggle");
    toggle.style.background = schedOn ? "var(--primary-color)" : "var(--divider-color,#ccc)";
    this.querySelector(".pp-sched-knob").style.left = schedOn ? "14px" : "2px";

    // Meals
    const mealsEl = this.querySelector(".pp-meals");
    const meals = [
      { label: "Meal 1", time: m1time, active: m1active },
      { label: "Meal 2", time: m2time, active: m2active },
      { label: "Meal 3", time: m3time, active: m3active },
    ];
    // Build meal rows if not yet built or count changed
    if (mealsEl.children.length !== meals.length) {
      mealsEl.innerHTML = "";
      meals.forEach(() => {
        const row = document.createElement("div");
        row.style.cssText = "display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--divider-color,#e0e0e0);border-radius:8px";
        row.innerHTML = `
          <div class="meal-dot" style="width:8px;height:8px;border-radius:50%;flex-shrink:0"></div>
          <div class="meal-label" style="font-size:12px;color:var(--secondary-text-color);width:44px;flex-shrink:0"></div>
          <div class="meal-time" style="font-size:13px;font-weight:500;flex:1"></div>`;
        mealsEl.appendChild(row);
      });
    }
    Array.from(mealsEl.children).forEach((row, i) => {
      const { label, time, active } = meals[i];
      const disabled = time === "Disabled" || time === "—";
      row.querySelector(".meal-dot").style.background = active ? battColor : "var(--divider-color,#e0e0e0)";
      row.querySelector(".meal-label").textContent = label;
      const timeEl = row.querySelector(".meal-time");
      timeEl.textContent = time;
      timeEl.style.color = disabled ? "var(--secondary-text-color)" : "var(--primary-text-color)";
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