// Authored diagnostic probe for task-04's written requirements. This is not a
// replacement SWE-bench evaluator. Run in the isolated pinned source workspace.
package main

import (
    "encoding/json"
    "fmt"
    "os"
    "reflect"

    "github.com/markphelps/flipt/config"
    "github.com/spf13/viper"
)

func load(text string) (map[string]interface{}, error) {
    viper.Reset()
    file, err := os.CreateTemp("", "worktrace-utility-*.yml")
    if err != nil { return nil, err }
    defer os.Remove(file.Name())
    if _, err = file.WriteString(text); err != nil { return nil, err }
    file.Close()
    cfg, err := config.Load(file.Name())
    if err != nil { return nil, err }
    blob, err := json.Marshal(cfg)
    if err != nil { return nil, err }
    result := map[string]interface{}{}
    err = json.Unmarshal(blob, &result)
    return result, err
}

func main() {
    result := map[string]interface{}{}
    custom, err := load("db:\n  max_idle_conn: 3\n  max_open_conn: 17\n  conn_max_lifetime: 2h\nmeta:\n  check_for_updates: false\n")
    if err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(2) }
    db := custom["database"].(map[string]interface{})
    meta := custom["meta"].(map[string]interface{})
    result["explicit_pool_values"] = db["maxIdleConn"] == float64(3) && db["maxOpenConn"] == float64(17) && db["connMaxLifetime"] == float64(7200000000000)
    result["explicit_false_flag"] = meta["checkForUpdates"] == false
    absent, err := load("{}\n")
    if err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(2) }
    absentMeta := absent["meta"].(map[string]interface{})
    result["absent_flag_false"] = absentMeta["checkForUpdates"] == false
    result["observed_absent_flag"] = absentMeta["checkForUpdates"]
    for name, path := range map[string]string{"default_fixture_equals_Default": "config/testdata/config/default.yml", "deprecated_fixture_equals_Default": "config/testdata/config/deprecated.yml"} {
        viper.Reset()
        cfg, e := config.Load(path)
        if e != nil { result[name] = nil; result[name+"_error"] = e.Error() } else { result[name] = reflect.DeepEqual(cfg, config.Default()) }
    }
    json.NewEncoder(os.Stdout).Encode(result)
}
