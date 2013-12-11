/* Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef MOD_PROXY_WSTUNNEL_H
#define MOD_PROXY_WSTUNNEL_H

/**
 * @file  mod_proxy_wstunnel.h
 * @brief Proxy Extension Module for Apache
 *
 * @defgroup MOD_PROXY_WSTUNNEL mod_proxy_wstunnel
 * @ingroup  APACHE_MODS
 * @{
 */

/*

   Also note numerous FIXMEs and CHECKMEs which should be eliminated.

   This code is once again experimental!

   Things to do:

   1. Make it completely work (for FTP too)

   2. HTTP/1.1

   Chuck Murcko <chuck@topsail.org> 02-06-01

 */

#include "mod_proxy.h"

/**
 * Create a HTTP request header brigade,  old_cl_val and old_te_val as required.
 * @parama p              pool
 * @param header_brigade  header brigade to use/fill
 * @param r               request
 * @param p_conn          proxy connection rec
 * @param worker          selected worker
 * @param conf            per-server proxy config
 * @param uri             uri
 * @param url             url
 * @param server_portstr  port as string
 * @param old_cl_val      stored old content-len val
 * @param old_te_val      stored old TE val
 * @return                OK or HTTP_EXPECTATION_FAILED
 */
PROXY_DECLARE(int) ap_proxy_create_hdrbrgd(apr_pool_t *p,
                                           apr_bucket_brigade *header_brigade,
                                           request_rec *r,
                                           proxy_conn_rec *p_conn,
                                           proxy_worker *worker,
                                           proxy_server_conf *conf,
                                           apr_uri_t *uri,
                                           char *url, char *server_portstr,
                                           char **old_cl_val,
                                           char **old_te_val);

/**
 * @param bucket_alloc  bucket allocator
 * @param r             request
 * @param p_conn        proxy connection
 * @param origin        connection rec of origin
 * @param  bb           brigade to send to origin
 * @param  flush        flush
 * @return              status (OK)
 */
PROXY_DECLARE(int) ap_proxy_pass_brigade(apr_bucket_alloc_t *bucket_alloc,
                                         request_rec *r, proxy_conn_rec *p_conn,
                                         conn_rec *origin, apr_bucket_brigade *bb,
                                         int flush);

#endif /*MOD_PROXY_WSTUNNEL_H*/
/** @} */
