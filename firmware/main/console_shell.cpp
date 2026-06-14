// =============================================================================
//  console_shell.cpp — REPL on USB-CDC for first-light bring-up.
// =============================================================================
#include "console_shell.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "esp_log.h"
#include "esp_console.h"
#include "argtable3/argtable3.h"

#include "vfo_si5351.h"
#include "front_panel.h"
#include "power_supply.h"
#include "fault_handler.h"
#include "encoders.h"

namespace shell {

namespace {
constexpr char TAG[] = "shell";

// ---- `vfo` command --------------------------------------------------------
struct {
    arg_str_t *action;   // "freq", "on", "off", "status"
    arg_int_t *hz;       // frequency in Hz (used only with "freq")
    arg_end_t *end;
} vfo_args;

int cmd_vfo(int argc, char **argv) {
    int nerr = arg_parse(argc, argv, (void **)&vfo_args);
    if (nerr != 0) {
        arg_print_errors(stderr, vfo_args.end, argv[0]);
        return 1;
    }

    const char *action = vfo_args.action->sval[0];
    if (std::strcmp(action, "freq") == 0) {
        if (vfo_args.hz->count == 0) {
            std::printf("usage: vfo freq <hz>\n");
            return 1;
        }
        uint32_t hz = (uint32_t)vfo_args.hz->ival[0];
        esp_err_t e = front_panel::set_freq_hz(hz);
        std::printf("vfo freq -> %lu Hz : %s\n",
                    (unsigned long)hz, esp_err_to_name(e));
        return (e == ESP_OK) ? 0 : 1;
    }
    if (std::strcmp(action, "on") == 0) {
        esp_err_t e = vfo::on();
        std::printf("vfo on : %s\n", esp_err_to_name(e));
        return (e == ESP_OK) ? 0 : 1;
    }
    if (std::strcmp(action, "off") == 0) {
        esp_err_t e = vfo::off();
        std::printf("vfo off : %s\n", esp_err_to_name(e));
        return (e == ESP_OK) ? 0 : 1;
    }
    if (std::strcmp(action, "status") == 0) {
        std::printf("vfo: %lu Hz, output %s\n",
                    (unsigned long)vfo::current_freq(),
                    vfo::is_on() ? "ON" : "off");
        return 0;
    }
    std::printf("unknown action '%s' (try freq|on|off|status)\n", action);
    return 1;
}

// ---- `status` command -----------------------------------------------------
int cmd_status(int, char **) {
    std::printf("--- xmitter status ---\n");
    std::printf("vfo   : %lu Hz, %s\n",
                (unsigned long)vfo::current_freq(),
                vfo::is_on() ? "ON" : "off");
    std::printf("step  : %lu Hz (idx %u)\n",
                (unsigned long)encoders::step_hz(),
                (unsigned)encoders::step_index());
    std::printf("power : %u %%\n", front_panel::power_pct());
    std::printf("psu   : ");
    switch (psu::state()) {
        case psu::State::Off:          std::printf("OFF\n"); break;
        case psu::State::WarmingUp:    std::printf("WARMING UP\n"); break;
        case psu::State::Ready:        std::printf("READY\n"); break;
        case psu::State::ShuttingDown: std::printf("SHUTTING DOWN\n"); break;
        case psu::State::Fault:        std::printf("FAULT\n"); break;
    }
    std::printf("fault : %s\n",
                fault::is_asserted() ? "ASSERTED" : "clear");
    return 0;
}

// ---- `step` command -------------------------------------------------------
struct {
    arg_int_t *idx;     // optional new index
    arg_end_t *end;
} step_args;

int cmd_step(int argc, char **argv) {
    int nerr = arg_parse(argc, argv, (void **)&step_args);
    if (nerr != 0) {
        arg_print_errors(stderr, step_args.end, argv[0]);
        return 1;
    }
    if (step_args.idx->count > 0) {
        encoders::set_step_index((size_t)step_args.idx->ival[0]);
    }
    std::printf("step = %lu Hz (idx %u)\n",
                (unsigned long)encoders::step_hz(),
                (unsigned)encoders::step_index());
    std::printf("table: ");
    for (size_t i = 0; i < encoders::FREQ_STEP_TABLE_LEN; ++i) {
        std::printf("[%u]=%lu%s", (unsigned)i,
                    (unsigned long)encoders::FREQ_STEP_HZ_TABLE[i],
                    (i + 1 < encoders::FREQ_STEP_TABLE_LEN) ? "  " : "\n");
    }
    return 0;
}

// ---- `psu` command --------------------------------------------------------
struct {
    arg_str_t *action;
    arg_end_t *end;
} psu_args;

int cmd_psu(int argc, char **argv) {
    int nerr = arg_parse(argc, argv, (void **)&psu_args);
    if (nerr != 0) {
        arg_print_errors(stderr, psu_args.end, argv[0]);
        return 1;
    }
    const char *a = psu_args.action->sval[0];
    if (std::strcmp(a, "on") == 0)  { return psu::on()  == ESP_OK ? 0 : 1; }
    if (std::strcmp(a, "off") == 0) { return psu::off() == ESP_OK ? 0 : 1; }
    std::printf("usage: psu on | psu off\n");
    return 1;
}

void register_commands() {
    // vfo
    vfo_args.action = arg_str1(nullptr, nullptr, "ACTION", "freq|on|off|status");
    vfo_args.hz     = arg_int0(nullptr, nullptr, "HZ", "frequency in Hz (for `freq`)");
    vfo_args.end    = arg_end(2);
    esp_console_cmd_t vfo_cmd = {};
    vfo_cmd.command  = "vfo";
    vfo_cmd.help     = "Control the Si5351 VFO";
    vfo_cmd.func     = &cmd_vfo;
    vfo_cmd.argtable = &vfo_args;
    ESP_ERROR_CHECK(esp_console_cmd_register(&vfo_cmd));

    // status
    esp_console_cmd_t status_cmd = {};
    status_cmd.command = "status";
    status_cmd.help    = "Print overall rig status";
    status_cmd.func    = &cmd_status;
    ESP_ERROR_CHECK(esp_console_cmd_register(&status_cmd));

    // step
    step_args.idx = arg_int0(nullptr, nullptr, "IDX",
                             "step-table index (omit to query)");
    step_args.end = arg_end(2);
    esp_console_cmd_t step_cmd = {};
    step_cmd.command  = "step";
    step_cmd.help     = "Show or set the frequency-step index";
    step_cmd.func     = &cmd_step;
    step_cmd.argtable = &step_args;
    ESP_ERROR_CHECK(esp_console_cmd_register(&step_cmd));

    // psu
    psu_args.action = arg_str1(nullptr, nullptr, "ACTION", "on|off");
    psu_args.end    = arg_end(2);
    esp_console_cmd_t psu_cmd = {};
    psu_cmd.command  = "psu";
    psu_cmd.help     = "Power-supply on/off (stub)";
    psu_cmd.func     = &cmd_psu;
    psu_cmd.argtable = &psu_args;
    ESP_ERROR_CHECK(esp_console_cmd_register(&psu_cmd));
}

}  // namespace

esp_err_t init() {
    // REPL config: USB-Serial-JTAG, history, prompt.
    esp_console_repl_t *repl = nullptr;
    esp_console_repl_config_t repl_cfg = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    repl_cfg.prompt          = "xmitter> ";
    repl_cfg.max_cmdline_length = 128;

    esp_console_dev_usb_serial_jtag_config_t hw_cfg =
        ESP_CONSOLE_DEV_USB_SERIAL_JTAG_CONFIG_DEFAULT();

    ESP_ERROR_CHECK(esp_console_new_repl_usb_serial_jtag(&hw_cfg, &repl_cfg, &repl));
    esp_console_register_help_command();
    register_commands();
    ESP_ERROR_CHECK(esp_console_start_repl(repl));

    ESP_LOGI(TAG, "USB-CDC shell ready (type 'help')");
    return ESP_OK;
}

}  // namespace shell
