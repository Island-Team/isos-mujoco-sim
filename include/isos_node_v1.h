#ifndef ISOS_NODE_V1_H
#define ISOS_NODE_V1_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Linux v1 node ABI. Byte spans are borrowed for the duration of each call. */
#define ISOS_NODE_ABI_VERSION 1u

typedef struct isos_node_handle isos_node_handle;

typedef struct {
  uint32_t abi_version;
  uint32_t struct_size;
  void *context;
  /* Emit a bounded JSON envelope. The host copies bytes before this returns. */
  int32_t (*emit)(void *context, const uint8_t *bytes, size_t length);
  /* Message is UTF-8, bounded, and must not contain secrets or payload data. */
  void (*log)(void *context, uint32_t level, const uint8_t *message, size_t length);
} isos_node_host_v1;

typedef struct {
  uint32_t abi_version;
  uint32_t struct_size;
  /* Config is bounded JSON containing the admitted instance, run and revision. */
  int32_t (*create)(const uint8_t *config, size_t length,
                    const isos_node_host_v1 *host, isos_node_handle **out);
  int32_t (*start)(isos_node_handle *node);
  /* Input is a bounded JSON data envelope; output uses host.emit. */
  int32_t (*input)(isos_node_handle *node, const uint8_t *bytes, size_t length);
  /* 1 = ready, 0 = degraded, negative = failed. */
  int32_t (*health)(isos_node_handle *node);
  /* Zero confirms quiescence and, for an actuator, owner stop proof. */
  int32_t (*stop)(isos_node_handle *node);
  void (*destroy)(isos_node_handle *node);
} isos_node_api_v1;

/* Required exported symbol. The returned table remains valid until dlclose. */
const isos_node_api_v1 *isos_node_v1(void);

#ifdef __cplusplus
}
#endif

#endif
