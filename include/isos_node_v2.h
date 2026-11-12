#ifndef ISOS_NODE_V2_H
#define ISOS_NODE_V2_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Linux v2 node ABI. Every byte span is borrowed for the call only. */
#define ISOS_NODE_ABI_V2 2u

typedef struct isos_node_v2_handle isos_node_v2_handle;

typedef struct {
  uint32_t abi_version;
  uint32_t struct_size;
  void *context;
  /* JSON {port,payload}; the host copies at most its declared output bound. */
  int32_t (*emit)(void *context, const uint8_t *bytes, size_t length);
  /* Sanitized UTF-8 text; never include raw command or image payloads. */
  void (*log)(void *context, uint32_t level, const uint8_t *bytes, size_t length);
  /* JSON stop proof, copied before return; at most 16 KiB. */
  int32_t (*stop_proof)(void *context, const uint8_t *bytes, size_t length);
} isos_node_host_v2;

typedef struct {
  uint32_t abi_version;
  uint32_t struct_size;
  /* JSON includes run_id, revision, instance, and a private service endpoint. */
  int32_t (*create)(const uint8_t *config, size_t length,
                    const isos_node_host_v2 *host, isos_node_v2_handle **out);
  int32_t (*start)(isos_node_v2_handle *node);
  /* Bounded JSON observation request; result is sent through host.emit. */
  int32_t (*observe)(isos_node_v2_handle *node, const uint8_t *bytes, size_t length);
  /* Bounded JSON Dispatcher-admitted envelope; result uses host.emit. */
  int32_t (*command)(isos_node_v2_handle *node, const uint8_t *bytes, size_t length);
  /* 1 ready, 0 degraded, negative failed. */
  int32_t (*health)(isos_node_v2_handle *node);
  /* Zero only with a run-bound proof emitted through host.stop_proof. */
  int32_t (*stop)(isos_node_v2_handle *node, const uint8_t *bytes, size_t length);
  void (*destroy)(isos_node_v2_handle *node);
} isos_node_api_v2;

/* The returned immutable table remains valid until dlclose. */
const isos_node_api_v2 *isos_node_v2(void);

#ifdef __cplusplus
}
#endif

#endif
