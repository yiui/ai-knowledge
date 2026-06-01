<template>
    <div class="chat">
      <div class="messages">
        <div v-for="(m, i) in messages" :key="i">
          <b>{{ m.role }}:</b> {{ m.text }}
        </div>
      </div>
  
      <input v-model="input" placeholder="请输入问题..." />
      <button @click="send">发送</button>
    </div>
  </template>
  
  <script setup>
  import { ref } from "vue";
  import { chat } from "@/api/chat";
  
  const input = ref("");
  const messages = ref([]);
  
  const send = async () => {
    const question = input.value;
  
    messages.value.push({ role: "user", text: question });
  
    const res = await chat(question);
  
    messages.value.push({
      role: "ai",
      text: res.data.answer
    });
  
    input.value = "";
  };
  </script>