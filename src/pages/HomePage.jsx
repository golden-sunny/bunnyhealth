import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import betterHomeImage from '../../picture/betterhome.png'
import healthHomeImage from '../../picture/healthhome.png'
import nightHomeImage from '../../picture/nighthome.png'
import sickHomeImage from '../../picture/sickhome.png'
import petNormalImage from '../../picture/宠物normal-removebg-preview.png'
import petBadImage from '../../picture/宠物状态不好-1-removebg-preview.png'
import petLowImage from '../../picture/宠物状态低-2-removebg-preview.png'
import petFiberImage from '../../picture/宠物缺膳食纤维-removebg-preview.png'

const API_BASE = '/api'
const DEFAULT_USER_ID = 1
const DEFAULT_PET_NAMES = ['Bunny', 'My Bunny']

const HOME_IMAGES = {
  betterhome: betterHomeImage,
  healthhome: healthHomeImage,
  nighthome: nightHomeImage,
  normal: healthHomeImage,
  sickhome: sickHomeImage,
}

const DISEASE_IMAGES = {
  fiber_mild: petFiberImage,
  fiber_severe: petFiberImage,
  iron_mild: petBadImage,
  iron_severe: petLowImage,
  iodine_mild: petBadImage,
  iodine_severe: petLowImage,
  vit_c_mild: petBadImage,
  vit_c_severe: petLowImage,
  calcium_mild: petBadImage,
  calcium_severe: petLowImage,
}

function getPetImage(status) {
  const diseases = status?.active_diseases || []
  const hasFiberProblem = diseases.some((disease) => disease.element === 'fiber')
  const hasSevereProblem = diseases.some((disease) => disease.severity === 'severe')
  const overallScore = status?.pet?.overall_score ?? 100
  const homeState = status?.home?.state

  if (hasFiberProblem) return petFiberImage
  if (hasSevereProblem || overallScore < 45 || homeState === 'dark') return petLowImage
  if (overallScore < 75 || homeState === 'sick') return petBadImage
  return petNormalImage
}

function shouldAskPetName(status) {
  const petName = status?.pet?.name?.trim()
  return !petName || DEFAULT_PET_NAMES.includes(petName)
}

export default function HomePage() {
  const fileInputRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [imageBase64, setImageBase64] = useState('')
  const [analysisResult, setAnalysisResult] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [notice, setNotice] = useState('')
  const [showCravingPanel, setShowCravingPanel] = useState(false)
  const [craving, setCraving] = useState('')
  const [location, setLocation] = useState('')
  const [cravingAdvice, setCravingAdvice] = useState(null)
  const [isCravingLoading, setIsCravingLoading] = useState(false)
  const [cravingError, setCravingError] = useState('')
  const [showPetPanel, setShowPetPanel] = useState(false)
  const [petStatus, setPetStatus] = useState(null)
  const [isPetLoading, setIsPetLoading] = useState(false)
  const [petError, setPetError] = useState('')
  const [showTaskPanel, setShowTaskPanel] = useState(false)
  const [healthTaskData, setHealthTaskData] = useState(null)
  const [isTaskLoading, setIsTaskLoading] = useState(false)
  const [taskError, setTaskError] = useState('')
  const [taskNotice, setTaskNotice] = useState('')
  const [completingTaskId, setCompletingTaskId] = useState('')
  const [petNameInput, setPetNameInput] = useState('')
  const [isNamingPet, setIsNamingPet] = useState(false)
  const [petNameError, setPetNameError] = useState('')

  const currentUserId = Number(localStorage.getItem('user_id')) || DEFAULT_USER_ID
  const currentPetName = shouldAskPetName(petStatus) ? '' : petStatus?.pet?.name

  const handleChoosePhoto = () => {
    setNotice('')
    fileInputRef.current?.click()
  }

  const analyzeMeal = async (base64Value) => {
    if (!base64Value) {
      setErrorMessage('先拍照或上传这一顿饭的照片。')
      return
    }

    setIsAnalyzing(true)
    setErrorMessage('')
    setNotice('')

    try {
      const response = await axios.post(`${API_BASE}/meals/analyze`, {
        user_id: currentUserId,
        food_name: '图片识别餐食',
        image_base64: base64Value,
      })

      setAnalysisResult(response.data)
      if (response.data.newly_collected_events?.length > 0) {
        setNotice(`解锁随机事件：${response.data.newly_collected_events.map((event) => event.title).join('、')}`)
      }
      fetchPetStatus({ silent: true })
      if (showTaskPanel) {
        fetchHealthTasks({ silent: true })
      }
    } catch (error) {
      console.error('Failed to analyze meal:', error)
      setErrorMessage('识别失败，请确认后端服务已经启动。')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleImageSelect = (event) => {
    const file = event.target.files?.[0]

    if (!file) {
      return
    }

    if (!file.type.startsWith('image/')) {
      setErrorMessage('请上传一张餐食照片。')
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result)
      const base64Value = result.split(',')[1] || result
      setSelectedFile(file)
      setPreviewUrl(result)
      setImageBase64(base64Value)
      setAnalysisResult(null)
      setErrorMessage('')
      analyzeMeal(base64Value)
    }
    reader.onerror = () => {
      setErrorMessage('照片读取失败，请重新选择。')
    }
    reader.readAsDataURL(file)
  }

  const handleAnalyzeMeal = () => {
    analyzeMeal(imageBase64)
  }

  const handleClearPhoto = () => {
    setSelectedFile(null)
    setPreviewUrl('')
    setImageBase64('')
    setAnalysisResult(null)
    setErrorMessage('')

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleOpenCravingPanel = () => {
    setShowCravingPanel((value) => !value)
    setNotice('')
  }

  const handleCravingSubmit = async (event) => {
    event.preventDefault()

    if (!craving.trim()) {
      setCravingError('先告诉我你想吃什么。')
      return
    }

    setIsCravingLoading(true)
    setCravingError('')
    setCravingAdvice(null)

    try {
      const response = await axios.post(`${API_BASE}/cravings/advice`, {
        user_id: currentUserId,
        craving: craving.trim(),
        location: location.trim() || '附近',
      })
      setCravingAdvice(response.data.advice)
      if (response.data.newly_collected_events?.length > 0) {
        setNotice(`解锁随机事件：${response.data.newly_collected_events.map((event) => event.title).join('、')}`)
      }
      if (showTaskPanel) {
        fetchHealthTasks({ silent: true })
      }
    } catch (error) {
      console.error('Failed to get craving advice:', error)
      setCravingError('建议生成失败，请确认后端服务已经启动。')
    } finally {
      setIsCravingLoading(false)
    }
  }

  const fetchPetStatus = async ({ silent = false } = {}) => {
    if (!silent) {
      setIsPetLoading(true)
    }
    setPetError('')

    try {
      const response = await axios.get(`${API_BASE}/pets/${currentUserId}/status`)
      setPetStatus(response.data)
      if (!petNameInput && !shouldAskPetName(response.data)) {
        setPetNameInput(response.data.pet?.name || '')
      }
    } catch (error) {
      console.error('Failed to fetch pet status:', error)
      setPetError('宠物状态加载失败，请确认后端服务已经启动。')
    } finally {
      if (!silent) {
        setIsPetLoading(false)
      }
    }
  }

  const handleOpenPetPanel = () => {
    const nextValue = !showPetPanel
    setShowPetPanel(nextValue)
    if (nextValue && !petStatus) {
      fetchPetStatus()
    }
    setNotice('')
  }

  const handleSavePetName = async (event) => {
    event.preventDefault()
    const nextName = petNameInput.trim()

    if (!nextName) {
      setPetNameError('给小宠物取一个名字吧。')
      return
    }

    setIsNamingPet(true)
    setPetNameError('')

    try {
      const response = await axios.patch(`${API_BASE}/pets/${currentUserId}/name`, {
        name: nextName,
      })
      setPetStatus(response.data)
      setHealthTaskData((current) => current ? { ...current, pet_status: response.data } : current)
      setNotice(`${nextName} 已经住进你的 home。`)
    } catch (error) {
      console.error('Failed to name pet:', error)
      const detail = error.response?.data?.detail
      setPetNameError(detail || '保存名字失败，请确认后端服务已经启动。')
    } finally {
      setIsNamingPet(false)
    }
  }

  const fetchHealthTasks = async ({ silent = false } = {}) => {
    if (!silent) {
      setIsTaskLoading(true)
    }
    setTaskError('')

    try {
      const response = await axios.get(`${API_BASE}/health-tasks/${currentUserId}/today`)
      setHealthTaskData(response.data)
      setPetStatus(response.data.pet_status)
      if (response.data.newly_collected_events?.length > 0) {
        setTaskNotice(`新事件已收集：${response.data.newly_collected_events.map((event) => event.title).join('、')}`)
      }
    } catch (error) {
      console.error('Failed to fetch health tasks:', error)
      setTaskError('健康任务加载失败，请确认后端服务已经启动。')
    } finally {
      if (!silent) {
        setIsTaskLoading(false)
      }
    }
  }

  const handleOpenTaskPanel = () => {
    const nextValue = !showTaskPanel
    setShowTaskPanel(nextValue)
    setNotice('')
    setTaskNotice('')
    if (nextValue && !healthTaskData) {
      fetchHealthTasks()
    }
  }

  useEffect(() => {
    fetchPetStatus({ silent: true })
  }, [])

  const handleCompleteTask = async (taskId) => {
    setCompletingTaskId(taskId)
    setTaskError('')
    setTaskNotice('')

    try {
      const response = await axios.post(`${API_BASE}/health-tasks/complete`, {
        user_id: currentUserId,
        task_id: taskId,
      })

      setHealthTaskData((current) => ({
        ...(current || {}),
        ...response.data,
        tasks: response.data.tasks || (current?.tasks || []).map((task) => (
          task.id === response.data.task?.id ? response.data.task : task
        )),
      }))
      setPetStatus(response.data.pet_status)

      const eventText = response.data.newly_collected_events?.length > 0
        ? ` 新事件：${response.data.newly_collected_events.map((event) => event.title).join('、')}`
        : ''
      setTaskNotice(`${response.data.message}${eventText}`)
    } catch (error) {
      console.error('Failed to complete health task:', error)
      setTaskError('任务完成失败，请稍后再试。')
    } finally {
      setCompletingTaskId('')
    }
  }

  return (
    <main className="min-h-screen bg-[#f7faf7] text-[#18221d]">
      <section className="mx-auto flex min-h-screen w-full max-w-md flex-col px-4 pb-4 pt-5">
        <header className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-[#29705a]">BunnyHealth</p>
            <h1 className="mt-1 text-2xl font-bold">
              {currentPetName ? `照顾 ${currentPetName}` : '拍下这一餐'}
            </h1>
          </div>
          <div
            className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-lg bg-[#e8f4ef]"
            aria-label="养成宠物"
          >
            <img
              src={petNormalImage}
              alt="养成宠物"
              className="h-full w-full object-contain p-1"
            />
          </div>
        </header>

        <div className="flex-1">
          {petStatus && shouldAskPetName(petStatus) && (
            <PetNameCard
              value={petNameInput}
              error={petNameError}
              isSaving={isNamingPet}
              onChange={setPetNameInput}
              onSubmit={handleSavePetName}
            />
          )}

          <button
            type="button"
            onClick={handleChoosePhoto}
            className="relative flex aspect-[3/4] w-full items-center justify-center overflow-hidden rounded-lg border-2 border-dashed border-[#8bc5af] bg-white text-left shadow-sm transition hover:border-[#29705a] focus:outline-none focus:ring-2 focus:ring-[#29705a] focus:ring-offset-2"
          >
            {previewUrl ? (
              <img
                src={previewUrl}
                alt="已上传的餐食照片"
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full flex-col items-center justify-center gap-4 px-8">
                <div className="flex h-32 w-32 items-center justify-center rounded-lg bg-[#e8f4ef] text-6xl text-[#29705a]">
                  拍
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold">点击拍照或上传</p>
                  <p className="mt-2 text-sm leading-6 text-[#61726a]">
                    上传这一顿饭的照片后，我会把图片发给后端识别。
                  </p>
                </div>
              </div>
            )}
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleImageSelect}
            className="hidden"
          />

          {selectedFile && (
            <div className="mt-3 flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm text-[#61726a] shadow-sm">
              <span className="truncate pr-3">{selectedFile.name}</span>
              <button
                type="button"
                onClick={handleClearPhoto}
                className="shrink-0 rounded-lg px-3 py-1 font-semibold text-[#d6534f] transition hover:bg-[#ffe8e6]"
              >
                重拍
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={handleAnalyzeMeal}
            disabled={!previewUrl || isAnalyzing}
            className="mt-4 w-full rounded-lg bg-[#29705a] px-5 py-4 text-base font-bold text-white shadow-sm transition hover:bg-[#1f5b49] disabled:cursor-not-allowed disabled:bg-[#a9b8b1]"
          >
            {!previewUrl
              ? '上传照片后自动识别'
              : isAnalyzing
                ? '正在识别...'
                : '重新识别这张照片'}
          </button>

          {errorMessage && (
            <p className="mt-3 rounded-lg border border-[#f3aaa6] bg-[#fff0ef] px-3 py-2 text-sm text-[#a83430]">
              {errorMessage}
            </p>
          )}

          {analysisResult && (
            <MealResult result={analysisResult} />
          )}

          {notice && (
            <p className="mt-3 rounded-lg bg-[#e8f4ef] px-3 py-2 text-sm text-[#29705a]">
              {notice}
            </p>
          )}

          {showCravingPanel && (
            <section className="mt-4 rounded-lg bg-white p-4 shadow-sm">
              <div className="mb-3">
                <p className="text-sm font-semibold text-[#29705a]">你想吃什么？</p>
                <h2 className="mt-1 text-xl font-bold">先说出来，我们一起选</h2>
              </div>

              <form onSubmit={handleCravingSubmit} className="space-y-3">
                <label className="block">
                  <span className="text-sm font-semibold text-[#40514a]">想吃的东西</span>
                  <input
                    type="text"
                    value={craving}
                    onChange={(event) => setCraving(event.target.value)}
                    placeholder="比如：炸鸡、奶茶、番茄牛腩饭"
                    className="mt-2 w-full rounded-lg border border-[#d8e5df] bg-[#f7faf7] px-3 py-3 text-sm outline-none transition focus:border-[#29705a] focus:ring-2 focus:ring-[#d8eee5]"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-semibold text-[#40514a]">附近位置</span>
                  <input
                    type="text"
                    value={location}
                    onChange={(event) => setLocation(event.target.value)}
                    placeholder="可选，比如：学校东门、公司楼下"
                    className="mt-2 w-full rounded-lg border border-[#d8e5df] bg-[#f7faf7] px-3 py-3 text-sm outline-none transition focus:border-[#29705a] focus:ring-2 focus:ring-[#d8eee5]"
                  />
                </label>

                <button
                  type="submit"
                  disabled={isCravingLoading}
                  className="w-full rounded-lg bg-[#29705a] px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:bg-[#1f5b49] disabled:cursor-not-allowed disabled:bg-[#a9b8b1]"
                >
                  {isCravingLoading ? '正在生成建议...' : '看看怎么吃更舒服'}
                </button>
              </form>

              {cravingError && (
                <p className="mt-3 rounded-lg border border-[#f3aaa6] bg-[#fff0ef] px-3 py-2 text-sm text-[#a83430]">
                  {cravingError}
                </p>
              )}

              {cravingAdvice && (
                <CravingAdvice advice={cravingAdvice} />
              )}
            </section>
          )}

          {showPetPanel && (
            <section className="mt-4 rounded-lg bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-[#29705a]">宠物状态</p>
                  <h2 className="mt-1 text-xl font-bold">小兔子的 home</h2>
                </div>
                <button
                  type="button"
                  onClick={() => fetchPetStatus()}
                  className="rounded-lg bg-[#e8f4ef] px-3 py-2 text-sm font-bold text-[#29705a]"
                >
                  刷新
                </button>
              </div>

              {isPetLoading && (
                <p className="rounded-lg bg-[#f7faf7] px-3 py-3 text-sm text-[#61726a]">
                  正在查看小兔子状态...
                </p>
              )}

              {petError && (
                <p className="rounded-lg border border-[#f3aaa6] bg-[#fff0ef] px-3 py-2 text-sm text-[#a83430]">
                  {petError}
                </p>
              )}

              {petStatus && (
                <PetStatusPanel status={petStatus} />
              )}
            </section>
          )}

          {showTaskPanel && (
            <section className="mt-4 rounded-lg bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-[#29705a]">健康任务</p>
                  <h2 className="mt-1 text-xl font-bold">今天照顾小兔子</h2>
                </div>
                <button
                  type="button"
                  onClick={() => fetchHealthTasks()}
                  className="rounded-lg bg-[#e8f4ef] px-3 py-2 text-sm font-bold text-[#29705a]"
                >
                  刷新
                </button>
              </div>

              {isTaskLoading && (
                <p className="rounded-lg bg-[#f7faf7] px-3 py-3 text-sm text-[#61726a]">
                  正在生成今天的小任务...
                </p>
              )}

              {taskError && (
                <p className="rounded-lg border border-[#f3aaa6] bg-[#fff0ef] px-3 py-2 text-sm text-[#a83430]">
                  {taskError}
                </p>
              )}

              {healthTaskData && (
                <HealthTasksPanel
                  data={healthTaskData}
                  notice={taskNotice}
                  completingTaskId={completingTaskId}
                  onComplete={handleCompleteTask}
                />
              )}
            </section>
          )}
        </div>

        <nav className="mt-5 grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={handleOpenCravingPanel}
            className={`rounded-lg px-2 py-3 text-sm font-bold shadow-sm transition ${
              showCravingPanel
                ? 'bg-[#29705a] text-white'
                : 'bg-[#ffcf5a] text-[#332400] hover:bg-[#f3bf43]'
            }`}
          >
            你想吃什么？
          </button>
          <button
            type="button"
            onClick={handleOpenPetPanel}
            className={`rounded-lg px-2 py-3 text-sm font-bold shadow-sm transition ${
              showPetPanel
                ? 'bg-[#29705a] text-white'
                : 'bg-white text-[#40514a] hover:bg-[#edf5f1]'
            }`}
          >
            宠物状态？
          </button>
          <button
            type="button"
            onClick={handleOpenTaskPanel}
            className={`rounded-lg px-2 py-3 text-sm font-bold shadow-sm transition ${
              showTaskPanel
                ? 'bg-[#29705a] text-white'
                : 'bg-white text-[#40514a] hover:bg-[#edf5f1]'
            }`}
          >
            健康任务
          </button>
        </nav>
      </section>
    </main>
  )
}

function PetNameCard({ value, error, isSaving, onChange, onSubmit }) {
  return (
    <section className="mb-4 rounded-lg border border-[#d8e5df] bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-[#e8f4ef]">
          <img
            src={petNormalImage}
            alt="待命名宠物"
            className="h-full w-full object-contain p-1"
          />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-[#29705a]">宠物命名</p>
          <h2 className="mt-1 text-lg font-bold text-[#18221d]">给你的伙伴取个名字</h2>
          <p className="mt-1 text-sm leading-6 text-[#61726a]">
            之后的 home、状态和任务都会用这个名字陪你一起养成。
          </p>
        </div>
      </div>

      <form onSubmit={onSubmit} className="mt-3 flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          maxLength={16}
          placeholder="比如：团团、小芽、饭饭"
          className="min-w-0 flex-1 rounded-lg border border-[#d8e5df] bg-[#f7faf7] px-3 py-3 text-sm outline-none transition focus:border-[#29705a] focus:ring-2 focus:ring-[#d8eee5]"
        />
        <button
          type="submit"
          disabled={isSaving}
          className="shrink-0 rounded-lg bg-[#29705a] px-4 py-3 text-sm font-bold text-white transition hover:bg-[#1f5b49] disabled:cursor-not-allowed disabled:bg-[#a9b8b1]"
        >
          {isSaving ? '保存中' : '保存'}
        </button>
      </form>

      {error && (
        <p className="mt-2 rounded-lg border border-[#f3aaa6] bg-[#fff0ef] px-3 py-2 text-sm text-[#a83430]">
          {error}
        </p>
      )}
    </section>
  )
}

function PetStatusPanel({ status }) {
  const homeImage = HOME_IMAGES[status.home?.image_key] || healthHomeImage
  const petImage = getPetImage(status)
  const recentMeals = status.recent_meals || []

  return (
    <div className="space-y-4">
      <div className="relative aspect-[4/3] overflow-hidden rounded-lg bg-[#dfeae5]">
        <img
          src={homeImage}
          alt={status.home?.message || '宠物房间'}
          className="h-full w-full object-cover"
        />
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/65 to-transparent px-4 pb-4 pt-12 text-white">
          <p className="text-sm font-semibold">{status.pet?.name || 'Bunny'}</p>
          <p className="mt-1 text-2xl font-bold">{status.pet?.status_text}</p>
          <p className="mt-1 text-sm leading-5 text-white/85">{status.home?.message}</p>
        </div>

        <div className="pointer-events-none absolute left-1/2 top-1/2 flex h-32 w-32 -translate-x-1/2 -translate-y-1/2 items-center justify-center">
          <img
            src={petImage}
            alt={status.pet?.status_text || '宠物状态'}
            className="h-full w-full object-contain drop-shadow-[0_12px_18px_rgba(0,0,0,0.28)]"
          />
        </div>

        {status.active_diseases?.slice(0, 4).map((disease, index) => {
          const image = DISEASE_IMAGES[disease.layer_name]
          if (!image) return null

          return (
            <div
              key={`${disease.layer_name}-${index}`}
              className="absolute"
              style={{
                top: `${12 + index * 14}%`,
                left: `${8 + index * 20}%`,
              }}
            >
              <img
                src={image}
                alt={disease.symptom}
                className="h-14 w-14 object-contain drop-shadow-[0_8px_12px_rgba(0,0,0,0.22)]"
              />
            </div>
          )
        })}
      </div>

      <div className="rounded-lg bg-[#f7faf7] p-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-bold text-[#18221d]">综合状态</p>
          <span className="text-lg font-bold text-[#29705a]">
            {status.pet?.overall_score}
          </span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#d8e5df]">
          <div
            className="h-full rounded-full bg-[#29705a]"
            style={{ width: `${status.pet?.overall_score || 0}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {status.attributes?.map((attribute) => (
          <AttributeBar key={attribute.key} attribute={attribute} />
        ))}
      </div>

      {status.active_diseases?.length > 0 && (
        <div className="rounded-lg bg-[#fffaf0] p-3">
          <p className="text-sm font-bold text-[#6a4b00]">当前提醒</p>
          <div className="mt-2 space-y-2">
            {status.active_diseases.map((disease) => (
              <p key={`${disease.element}-${disease.severity}`} className="text-sm leading-6 text-[#6f6250]">
                {disease.symptom}
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-lg bg-[#f1f6f3] p-3">
        <p className="text-sm font-bold text-[#18221d]">最近拍照饮食</p>
        <p className="mt-1 text-sm leading-6 text-[#61726a]">
          健康 {status.history_summary?.healthy_count || 0} 次，不健康 {status.history_summary?.unhealthy_count || 0} 次，油炸快餐 {status.history_summary?.fried_count || 0} 次。
        </p>
        <div className="mt-3 space-y-2">
          {recentMeals.length > 0 ? recentMeals.slice(0, 5).map((meal) => (
            <div key={meal.id} className="flex items-center justify-between rounded-lg bg-white px-3 py-2">
              <div>
                <p className="text-sm font-bold text-[#18221d]">{meal.food}</p>
                <p className="text-xs text-[#61726a]">{meal.dish_category} · {meal.food_type}</p>
              </div>
              <span className={`rounded-lg px-2 py-1 text-xs font-bold ${
                meal.is_healthy
                  ? 'bg-[#e3f6e9] text-[#27723d]'
                  : 'bg-[#fff0ef] text-[#a83430]'
              }`}
              >
                {meal.is_healthy ? '健康' : '负担'}
              </span>
            </div>
          )) : (
            <p className="rounded-lg bg-white px-3 py-3 text-sm text-[#61726a]">
              还没有历史拍照记录，上传几餐后 home 会开始变化。
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function HealthTasksPanel({ data, notice, completingTaskId, onComplete }) {
  const tasks = data.tasks || []
  const events = data.event_collection || []
  const completedCount = tasks.filter((task) => task.completed).length

  return (
    <div className="space-y-4">
      <div className="rounded-lg bg-[#f7faf7] p-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-bold text-[#18221d]">每日随机任务</p>
            <p className="mt-1 text-sm leading-6 text-[#61726a]">
              每天刷新 2 个小任务，完成后会提升宠物状态值。
            </p>
          </div>
          <span className="shrink-0 rounded-lg bg-white px-3 py-2 text-sm font-bold text-[#29705a]">
            {completedCount}/{tasks.length || 2}
          </span>
        </div>
      </div>

      {notice && (
        <p className="rounded-lg border border-[#8bc5af] bg-[#e8f4ef] px-3 py-2 text-sm font-semibold text-[#29705a]">
          {notice}
        </p>
      )}

      <div className="space-y-3">
        {tasks.map((task) => (
          <div key={task.id} className="rounded-lg border border-[#d8e5df] bg-white p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="rounded-lg bg-[#e8f4ef] px-2 py-1 text-xs font-bold text-[#29705a]">
                  {task.tag}
                </span>
                <h3 className="mt-2 text-lg font-bold text-[#18221d]">{task.title}</h3>
                <p className="mt-1 text-sm leading-6 text-[#61726a]">{task.description}</p>
              </div>
              <button
                type="button"
                onClick={() => onComplete(task.id)}
                disabled={task.completed || completingTaskId === task.id}
                className={`shrink-0 rounded-lg px-3 py-2 text-sm font-bold transition ${
                  task.completed
                    ? 'bg-[#e3f6e9] text-[#27723d]'
                    : 'bg-[#29705a] text-white hover:bg-[#1f5b49]'
                } disabled:cursor-not-allowed`}
              >
                {task.completed
                  ? '已完成'
                  : completingTaskId === task.id
                    ? '记录中'
                    : '完成'}
              </button>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {task.effect_items?.map((effect) => (
                <span
                  key={`${task.id}-${effect.key}`}
                  className="rounded-lg bg-[#f1f6f3] px-2 py-1 text-xs font-bold text-[#40514a]"
                >
                  {effect.label}{effect.value > 0 ? `+${effect.value}` : effect.value}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-lg bg-[#f1f6f3] p-3">
        <p className="text-sm font-bold text-[#18221d]">随机事件触发</p>
        <p className="mt-1 text-sm leading-6 text-[#61726a]">
          拍照次数、询问次数、宠物状态值都会触发小事件。收集到的事件会点亮，未收集的先保留剪影。
        </p>
      </div>

      <EventCollection events={events} />
    </div>
  )
}

function EventCollection({ events }) {
  if (!events?.length) {
    return (
      <p className="rounded-lg bg-[#f7faf7] px-3 py-3 text-sm text-[#61726a]">
        还没有事件图鉴，完成任务或多记录几餐后会开始出现。
      </p>
    )
  }

  return (
    <div>
      <p className="mb-2 text-sm font-bold text-[#18221d]">事件图鉴</p>
      <div className="grid grid-cols-2 gap-2">
        {events.map((event) => (
          <div
            key={event.id}
            className={`rounded-lg p-3 ${
              event.collected
                ? 'bg-white text-[#18221d] shadow-sm'
                : 'bg-[#eef2f0] text-[#718078]'
            }`}
          >
            <div className={`mb-3 flex h-16 items-center justify-center rounded-lg text-2xl font-bold ${
              event.collected
                ? 'bg-[#e8f4ef] text-[#29705a]'
                : 'bg-[#d8e0dc] text-[#9aa7a0]'
            }`}
            >
              {event.collected ? (
                <img
                  src={petNormalImage}
                  alt="已收集事件"
                  className="h-full w-full object-contain p-1"
                />
              ) : '?'}
            </div>
            <p className="text-sm font-bold">{event.title}</p>
            <p className="mt-1 text-xs leading-5">{event.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function AttributeBar({ attribute }) {
  const value = attribute.value || 0
  const good = attribute.is_inverse ? value <= 40 : value >= 80
  const warning = attribute.is_inverse ? value > 60 : value < 60
  const barColor = good ? '#29705a' : warning ? '#d6534f' : '#d4a62a'

  return (
    <div className="rounded-lg bg-[#f7faf7] p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-bold text-[#40514a]">{attribute.label}</p>
        <span className="text-sm font-bold text-[#18221d]">{value}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-[#d8e5df]">
        <div
          className="h-full rounded-full"
          style={{ width: `${value}%`, backgroundColor: barColor }}
        />
      </div>
    </div>
  )
}

function CravingAdvice({ advice }) {
  return (
    <div className="mt-4 space-y-4">
      <div className="rounded-lg bg-[#f7faf7] p-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-[#61726a]">想吃</p>
            <h3 className="mt-1 text-lg font-bold">{advice.craving}</h3>
          </div>
          <span className={`shrink-0 rounded-lg px-3 py-1 text-sm font-bold ${
            advice.is_healthy_choice
              ? 'bg-[#e3f6e9] text-[#27723d]'
              : 'bg-[#fff0ef] text-[#a83430]'
          }`}
          >
            {advice.is_healthy_choice ? '可以吃' : '换个吃法'}
          </span>
        </div>
        <p className="mt-3 text-sm leading-6 text-[#40514a]">
          {advice.health_summary}
        </p>
        <p className="mt-2 text-sm leading-6 text-[#61726a]">
          {advice.emotional_support}
        </p>
        <p className="mt-2 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-[#29705a]">
          {advice.better_choice_tip}
        </p>
      </div>

      {advice.possible_missing_nutrients?.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-bold text-[#18221d]">可能需要补一点</p>
          <div className="space-y-2">
            {advice.possible_missing_nutrients.map((nutrient) => (
              <div key={nutrient.name} className="rounded-lg bg-[#fffaf0] p-3">
                <p className="text-sm font-bold text-[#6a4b00]">{nutrient.name}</p>
                <p className="mt-1 text-sm leading-6 text-[#6f6250]">{nutrient.reason}</p>
                {nutrient.food_sources?.length > 0 && (
                  <p className="mt-1 text-xs font-semibold text-[#8a6a1f]">
                    可选：{nutrient.food_sources.join('、')}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <p className="mb-2 text-sm font-bold text-[#18221d]">附近餐馆菜单</p>
        <div className="space-y-3">
          {advice.restaurant_menus?.map((restaurant) => (
            <div key={restaurant.restaurant_name} className="rounded-lg bg-[#f1f6f3] p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="font-bold text-[#18221d]">{restaurant.restaurant_name}</p>
                <span className="shrink-0 text-xs font-semibold text-[#61726a]">
                  {restaurant.distance_hint}
                </span>
              </div>
              <div className="mt-3 space-y-2">
                {restaurant.menu_items?.map((item) => (
                  <div key={`${restaurant.restaurant_name}-${item.name}`} className="rounded-lg bg-white p-3">
                    <p className="text-sm font-bold text-[#29705a]">{item.name}</p>
                    <p className="mt-1 text-sm leading-6 text-[#61726a]">{item.reason}</p>
                    {item.nutrient_focus?.length > 0 && (
                      <p className="mt-1 text-xs font-semibold text-[#40514a]">
                        重点：{item.nutrient_focus.join('、')}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function MealResult({ result }) {
  const analysis = result.analysis
  const hp = result.pet_current_state?.hp || {}

  return (
    <section className="mt-4 rounded-lg bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[#29705a]">识别结果</p>
          <h2 className="mt-1 text-xl font-bold">{analysis.food}</h2>
          {(analysis.dish_category || analysis.food_type) && (
            <p className="mt-1 text-sm font-semibold text-[#61726a]">
              {[analysis.dish_category, analysis.food_type].filter(Boolean).join(' · ')}
            </p>
          )}
        </div>
        <span className={`rounded-lg px-3 py-1 text-sm font-bold ${
          analysis.is_healthy
            ? 'bg-[#e3f6e9] text-[#27723d]'
            : 'bg-[#fff0ef] text-[#a83430]'
        }`}
        >
          {analysis.is_healthy ? '健康' : '需注意'}
        </span>
      </div>

      <p className="mt-3 text-sm leading-6 text-[#61726a]">
        {analysis.reasoning}
      </p>

      <div className="mt-4 grid grid-cols-3 gap-2">
        <Nutrient label="活力" value={hp.health} />
        <Nutrient label="脂肪" value={hp.fat} />
        <Nutrient label="铁" value={hp.iron} />
        <Nutrient label="钙" value={hp.calcium} />
        <Nutrient label="碘" value={hp.iodine} />
        <Nutrient label="维C" value={hp.vit_c} />
        <Nutrient label="纤维" value={hp.fiber} />
      </div>
    </section>
  )
}

function Nutrient({ label, value = 0 }) {
  return (
    <div className="rounded-lg bg-[#f1f6f3] px-2 py-3 text-center">
      <p className="text-xs font-semibold text-[#61726a]">{label}</p>
      <p className="mt-1 text-sm font-bold text-[#18221d]">{value}</p>
    </div>
  )
}
