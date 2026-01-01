import type { Controller } from "../index"
import { Empty } from "@shared/proto/common"
import { UpdateApiConfigurationRequest } from "@shared/proto/models"
import { updateApiConfiguration } from "../../storage/state"
import { buildApiHandler } from "@api/index"
import { convertProtoToApiConfiguration } from "@shared/proto-conversions/models/api-configuration-conversion"

/**
 * Updates API configuration
 * @param controller The controller instance
 * @param request The update API configuration request
 * @returns Empty response
 */
export async function updateApiConfigurationProto(
	controller: Controller,
	request: UpdateApiConfigurationRequest,
): Promise<Empty> {
	const startTime = performance.now()
	console.log("[PERF] updateApiConfigurationProto: Starting provider switch")

	try {
		if (!request.apiConfiguration) {
			console.log("[APICONFIG: updateApiConfigurationProto] API configuration is required")
			throw new Error("API configuration is required")
		}

		// Convert proto ApiConfiguration to application ApiConfiguration
		const conversionStart = performance.now()
		const appApiConfiguration = convertProtoToApiConfiguration(request.apiConfiguration)
		const conversionEnd = performance.now()
		console.log(`[PERF] Proto conversion took: ${conversionEnd - conversionStart}ms`)

		// Update the API configuration in storage
		const storageStart = performance.now()
		await updateApiConfiguration(controller.context, appApiConfiguration)
		const storageEnd = performance.now()
		console.log(`[PERF] Storage update took: ${storageEnd - storageStart}ms`)

		// Update the task's API handler if there's an active task
		const apiHandlerStart = performance.now()
		if (controller.task) {
			controller.task.api = buildApiHandler(appApiConfiguration)
		}
		const apiHandlerEnd = performance.now()
		console.log(`[PERF] API handler update took: ${apiHandlerEnd - apiHandlerStart}ms`)

		// Post updated state to webview
		const statePostStart = performance.now()
		await controller.postStateToWebview()
		const statePostEnd = performance.now()
		console.log(`[PERF] State post to webview took: ${statePostEnd - statePostStart}ms`)

		const totalTime = performance.now() - startTime
		console.log(`[PERF] Total updateApiConfigurationProto took: ${totalTime}ms`)

		return Empty.create()
	} catch (error) {
		const totalTime = performance.now() - startTime
		console.error(`[PERF] Failed to update API configuration after ${totalTime}ms: ${error}`)
		throw error
	}
}
