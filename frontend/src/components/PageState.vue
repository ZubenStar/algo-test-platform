<template>
  <div v-if="loading" v-loading="true" class="page-state"></div>
  <el-empty v-else-if="empty" :description="description" />
  <slot v-else />
</template>

<script setup>
defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
  empty: {
    type: Boolean,
    default: false,
  },
  description: {
    type: String,
    default: '暂无数据',
  },
})
</script>

<style scoped>
.page-state {
  min-height: 200px;
}
</style>
