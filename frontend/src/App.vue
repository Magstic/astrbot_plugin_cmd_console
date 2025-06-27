<template>
  <v-app>
    <v-main>
      <v-container class="fill-height" fluid>
        <v-row align="center" justify="center">
          <v-col cols="12" sm="8" md="6">
            <!-- 认证界面 -->
            <v-card v-if="!isAuthenticated" elevation="12">
              <v-toolbar color="primary" dark>
                <v-toolbar-title>身份验证</v-toolbar-title>
              </v-toolbar>
              <v-card-text>
                <p class="subheading">请输入在机器人后台日志中显示的访问 Token。</p>
                <v-form @submit.prevent="submitToken">
                  <v-text-field
                    v-model="inputToken"
                    label="访问 Token"
                    prepend-icon="mdi-key"
                    type="password"
                    :error-messages="authError"
                    required
                  ></v-text-field>
                  <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn type="submit" color="primary" :loading="authLoading">验证</v-btn>
                  </v-card-actions>
                </v-form>
              </v-card-text>
            </v-card>

            <!-- 主内容界面 -->
            <v-card v-else elevation="10">
              <v-card-title class="d-flex align-center">
                <v-icon left>mdi-powershell</v-icon>
                <span class="ml-2">指令管理中心</span>
              </v-card-title>
              <v-card-subtitle>在这里可以单独启用或禁用插件中的具体指令。</v-card-subtitle>

              <v-card-text>
                <v-alert v-if="error" type="error" dense class="mb-4">{{ error }}</v-alert>

                <div v-if="loading" class="text-center pa-5">
                  <v-progress-circular indeterminate color="primary"></v-progress-circular>
                  <p class="mt-2">正在加载指令列表...</p>
                </div>

                <div v-else>
                  <v-expansion-panels variant="accordion">
                    <v-expansion-panel v-for="(commands, pluginName) in groupedCommands" :key="pluginName">
                      <v-expansion-panel-title>
                        <v-icon left class="mr-2">mdi-puzzle-outline</v-icon>
                        {{ pluginName }} ({{ commands.length }} 条指令)
                      </v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <v-table dense>
                          <thead>
                            <tr>
                              <th class="text-left">指令/命令</th>
                              <th class="text-left">描述</th>
                              <th class="text-center">状态 (启用/禁用)</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="command in commands" :key="command.handler_full_name">
                              <td><code>{{ command.command }}</code></td>
                              <td>{{ command.description }}</td>
                              <td class="text-center">
                                <v-switch
                                  v-model="command.activated"
                                  color="primary"
                                  hide-details
                                  inset
                                  @change="() => toggleCommand(command)"
                                ></v-switch>
                              </td>
                            </tr>
                          </tbody>
                        </v-table>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import axios from 'axios';

interface Command {
  handler_full_name: string;
  plugin_name: string;
  command: string;
  description: string;
  activated: boolean;
}

// 认证状态
const isAuthenticated = ref(false);
const inputToken = ref('');
const authLoading = ref(false);
const authError = ref<string | null>(null);

// 主内容状态
const commands = ref<Command[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// 配置 axios 实例，用于自动附加 Token
const apiClient = axios.create();

apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('authToken');
  if (token) {
    // 使用行业标准的 Authorization 请求头
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

const submitToken = async () => {
  authLoading.value = true;
  authError.value = null;
  const trimmedToken = inputToken.value.trim();
  try {
    // 在首次验证时，也使用标准的 Authorization 请求头
    await axios.get('/api/verify', {
      headers: { 'Authorization': `Bearer ${trimmedToken}` }
    });
    localStorage.setItem('authToken', trimmedToken);
    isAuthenticated.value = true;
    await fetchCommands(); // 认证成功后加载数据
  } catch (err) {
    authError.value = 'Token 无效或已过期，请重试。';
    localStorage.removeItem('authToken');
  } finally {
    authLoading.value = false;
  }
};

const fetchCommands = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await apiClient.get<Command[]>('/api/commands');
    commands.value = response.data;
  } catch (err: any) {
    console.error('Failed to fetch commands:', err);
    if (err.response?.status === 401) {
        error.value = '认证失败，请重新验证 Token。';
        isAuthenticated.value = false;
        localStorage.removeItem('authToken');
    } else {
        error.value = '无法加载指令列表。请检查后端服务是否正常运行。';
    }
  } finally {
    loading.value = false;
  }
};

const toggleCommand = async (command: Command) => {
  const originalStatus = command.activated;
  try {
    await apiClient.post('/api/commands/toggle', {
      handler_full_name: command.handler_full_name,
    });
  } catch (err: any) {
    console.error('Failed to toggle command:', err);
    error.value = `操作失败: ${err.response?.data?.detail || err.message}`;
    // 发生错误时，恢复UI状态
    command.activated = originalStatus;
  }
};

const groupedCommands = computed(() => {
  const groups: Record<string, Command[]> = {};
  for (const command of commands.value) {
    const pluginName = command.plugin_name;
    if (!groups[pluginName]) {
      groups[pluginName] = [];
    }
    groups[pluginName].push(command);
  }
  return groups;
});

onMounted(() => {
  const token = localStorage.getItem('authToken');
  if (token) {
    inputToken.value = token;
    // 自动尝试用已存储的 Token 验证
    submitToken();
  } else {
    // 如果没有 Token，则停留在登录页面，并将 loading 设置为 false
    loading.value = false;
  }
});
</script>

<style scoped>
code {
  background-color: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
}
.v-table th {
  font-weight: bold !important;
}
</style>
